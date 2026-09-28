"""Copy REALSYNCADE/SCDA-Experimental's latest.json onto this repository's `experimental` branch.

Every launcher reads the experimental channel from
raw.githubusercontent.com/REALSYNCADE/SCDA-Launcher/experimental/latest.json, which
is compiled into the exe. Collaborators publish in SCDA-Experimental; this job
carries their channel file here once it passes every check below. It runs in a
checkout of the `experimental` branch and pushes only there.

Checks, all of which must hold:
  * track is "experimental" and the version looks like 2026.09.28-x35
  * bundle_url is exactly the pre-release asset exp-v<version>/scda-ce-exp-<version>.scdaupd
    in SCDA-Experimental, or in this repository (for a roll-back to an older build)
  * that release exists, is a pre-release and not a draft, and carries the asset
  * the downloaded bundle's size and sha256 match latest.json
  * the bundle's manifest names the experimental track and the same version
  * a version already live here is never republished with different bytes
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

SOURCE = "REALSYNCADE/SCDA-Experimental"
HOME = "REALSYNCADE/SCDA-Launcher"
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}-x\d+$")
URL_RE = re.compile(r"^https://github\.com/(REALSYNCADE/SCDA-(?:Experimental|Launcher))"
                    r"/releases/download/exp-v([^/]+)/scda-ce-exp-([^/]+)\.scdaupd$")
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path, raw=False):
    headers = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "scda-experimental-mirror"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def refuse(msg):
    # an ::error annotation on the run, but exit 0: a refused file stays refused on
    # every scheduled run, and a failing run every five minutes would be mail spam
    print("::error title=experimental channel NOT mirrored::%s" % msg)
    summary(":x: not mirrored: %s" % msg)
    sys.exit(0)


def summary(line):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(line)


def main():
    incoming = api("repos/%s/contents/latest.json" % SOURCE, raw=True)
    if incoming is None:
        summary("SCDA-Experimental has no latest.json yet; nothing to do.")
        return
    current = open("latest.json", "rb").read() if os.path.isfile("latest.json") else b""
    if incoming == current:
        summary("up to date: %s" % json.loads(current)["version"])
        return

    try:
        data = json.loads(incoming)
    except ValueError as exc:
        refuse("latest.json is not JSON (%s)" % exc)
    version = str(data.get("version", ""))
    if data.get("track") != "experimental":
        refuse("track is %r, not 'experimental'" % data.get("track"))
    if not VERSION_RE.match(version):
        refuse("version %r does not look like 2026.09.28-x35" % version)
    m = URL_RE.match(str(data.get("bundle_url", "")))
    if not m or m.group(2) != version or m.group(3) != version:
        refuse("bundle_url %r is not exp-v%s/scda-ce-exp-%s.scdaupd in SCDA-Experimental or SCDA-Launcher"
               % (data.get("bundle_url"), version, version))
    repo, tag, asset_name = m.group(1), "exp-v" + version, "scda-ce-exp-%s.scdaupd" % version
    if current:
        live = json.loads(current)
        if live.get("version") == version and live.get("sha256") != data.get("sha256"):
            refuse("%s is already live with other bytes; publish it under a new version" % version)

    release = api("repos/%s/releases/tags/%s" % (repo, tag))
    if release is None:
        refuse("release %s does not exist in %s" % (tag, repo))
    release = json.loads(release)
    if not release.get("prerelease") or release.get("draft"):
        refuse("release %s in %s must be a published PRE-release" % (tag, repo))
    asset = next((a for a in release.get("assets", []) if a["name"] == asset_name), None)
    if asset is None:
        refuse("release %s carries no %s" % (tag, asset_name))
    if asset["size"] != data.get("size"):
        refuse("asset size %s but latest.json says %s" % (asset["size"], data.get("size")))

    h = hashlib.sha256()
    with tempfile.TemporaryFile() as tmp:
        with urllib.request.urlopen(urllib.request.Request(
                asset["browser_download_url"], headers={"User-Agent": "scda-experimental-mirror"}),
                timeout=300) as resp:
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                h.update(chunk)
                tmp.write(chunk)
        if tmp.tell() != data.get("size") or h.hexdigest() != data.get("sha256"):
            refuse("downloaded bundle is %d B sha256 %s; latest.json says %s B %s"
                   % (tmp.tell(), h.hexdigest(), data.get("size"), data.get("sha256")))
        tmp.seek(0)
        try:
            manifest = json.loads(zipfile.ZipFile(tmp).read("manifest.json"))
        except (zipfile.BadZipFile, KeyError, ValueError) as exc:
            refuse("bundle has no readable manifest.json (%s)" % exc)
    if manifest.get("track") != "experimental" or manifest.get("version") != version:
        refuse("bundle manifest says %s %s" % (manifest.get("track"), manifest.get("version")))

    with open("latest.json", "wb") as fh:
        fh.write(incoming)
    git = lambda *a: subprocess.run(["git"] + list(a), check=True)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", "latest.json")
    git("commit", "-m", "Experimental branch: %s (mirrored from %s)\n\n%s" % (version, SOURCE, data.get("notes", "")))
    git("push", "origin", "HEAD:experimental")
    summary(":white_check_mark: experimental channel now %s (%s)" % (version, repo))


if __name__ == "__main__":
    main()
