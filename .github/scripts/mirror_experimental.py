"""Carry a build published in the private REALSYNCADE/SCDA-Experimental to players.

Every launcher reads the experimental channel from
raw.githubusercontent.com/REALSYNCADE/SCDA-Launcher/experimental/latest.json (compiled
into the exe) and downloads the bundle that file names without logging in. The
source repository is private, so a player cannot read its releases. This job
therefore does two things once a new latest.json passes every check below:

  1. copies the bundle into a public PRE-release exp-v<version> of this repository
  2. commits latest.json to the `experimental` branch with bundle_url pointing at
     that copy

It runs in a checkout of the `experimental` branch and pushes only there. It
reads the source with the secret EXPERIMENTAL_READ_TOKEN (a fine-grained token
with read access to SCDA-Experimental's contents) and writes here with the
workflow's own GITHUB_TOKEN.

Checks, all of which must hold:
  * track is "experimental" and the version looks like 2026.09.28-x35
  * bundle_url is exactly the pre-release asset exp-v<version>/scda-ce-exp-<version>.scdaupd
    in SCDA-Experimental, or in this repository (a roll-back to an older build)
  * that release exists, is a pre-release and not a draft, and carries the asset
  * the downloaded bundle's size and sha256 match latest.json
  * the bundle's manifest names the experimental track and the same version
  * a version already live here is never republished with different bytes
  * a copy already in this repository under the same tag has the same bytes
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
SOURCE_TOKEN = os.environ.get("EXPERIMENTAL_TOKEN", "")
HOME_TOKEN = os.environ.get("GITHUB_TOKEN", "")
UA = "scda-experimental-mirror"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def token_for(repo):
    return SOURCE_TOKEN if repo == SOURCE else HOME_TOKEN


def api(path, raw=False, token=None, accept=None):
    headers = {"Accept": accept or ("application/vnd.github.raw" if raw else "application/vnd.github+json"),
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def download_asset(repo, asset_id, out, expect_size, expect_sha):
    """The asset through the API (works on a private repository), hashed on the way.

    The API answers with a redirect to a signed storage URL that refuses a request
    still carrying the Authorization header, so the redirect is followed by hand.
    """
    headers = {"Accept": "application/octet-stream", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA}
    token = token_for(repo)
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://api.github.com/repos/%s/releases/assets/%s" % (repo, asset_id),
                                 headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        resp = opener.open(req, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise
        resp = urllib.request.urlopen(urllib.request.Request(exc.headers["Location"], headers={"User-Agent": UA}),
                                      timeout=600)
    h = hashlib.sha256()
    size = 0
    with resp:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
            out.write(chunk)
    return size == expect_size and h.hexdigest() == expect_sha, size, h.hexdigest()


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


def gh(*args):
    env = dict(os.environ, GH_TOKEN=HOME_TOKEN)
    subprocess.run(["gh"] + list(args), check=True, env=env)


def release(repo, tag):
    data = api("repos/%s/releases/tags/%s" % (repo, tag), token=token_for(repo))
    return json.loads(data) if data else None


def main():
    if not SOURCE_TOKEN:
        refuse("the secret EXPERIMENTAL_READ_TOKEN is not set on %s, so the private %s cannot be read"
               % (HOME, SOURCE))
    incoming = api("repos/%s/contents/latest.json" % SOURCE, raw=True, token=SOURCE_TOKEN)
    if incoming is None:
        summary("%s has no latest.json yet (or the token cannot read it); nothing to do." % SOURCE)
        return
    current = json.loads(open("latest.json", "rb").read()) if os.path.isfile("latest.json") else {}
    try:
        data = json.loads(incoming)
    except ValueError as exc:
        refuse("latest.json is not JSON (%s)" % exc)
    version = str(data.get("version", ""))
    if current.get("version") == version and current.get("sha256") == data.get("sha256"):
        summary("up to date: %s" % version)
        return

    if data.get("track") != "experimental":
        refuse("track is %r, not 'experimental'" % data.get("track"))
    if not VERSION_RE.match(version):
        refuse("version %r does not look like 2026.09.28-x35" % version)
    m = URL_RE.match(str(data.get("bundle_url", "")))
    if not m or m.group(2) != version or m.group(3) != version:
        refuse("bundle_url %r is not exp-v%s/scda-ce-exp-%s.scdaupd in %s or %s"
               % (data.get("bundle_url"), version, version, SOURCE, HOME))
    repo, tag, asset_name = m.group(1), "exp-v" + version, "scda-ce-exp-%s.scdaupd" % version
    if current.get("version") == version:
        refuse("%s is already live with other bytes; publish it under a new version" % version)

    rel = release(repo, tag)
    if rel is None:
        refuse("release %s does not exist in %s" % (tag, repo))
    if not rel.get("prerelease") or rel.get("draft"):
        refuse("release %s in %s must be a published PRE-release" % (tag, repo))
    asset = next((a for a in rel.get("assets", []) if a["name"] == asset_name), None)
    if asset is None:
        refuse("release %s carries no %s" % (tag, asset_name))
    if asset["size"] != data.get("size"):
        refuse("asset size %s but latest.json says %s" % (asset["size"], data.get("size")))

    # the public copy this repository may already hold (a roll-back, or a re-run
    # after the upload succeeded and the push did not)
    home_rel = release(HOME, tag) if repo != HOME else rel
    home_asset = next((a for a in (home_rel or {}).get("assets", []) if a["name"] == asset_name), None)

    with tempfile.NamedTemporaryFile(suffix=".scdaupd", delete=False) as tmp:
        path = tmp.name
    try:
        with open(path, "wb") as fh:
            ok, size, digest = download_asset(repo, asset["id"], fh, data.get("size"), data.get("sha256"))
        if not ok:
            refuse("downloaded bundle is %d B sha256 %s; latest.json says %s B %s"
                   % (size, digest, data.get("size"), data.get("sha256")))
        try:
            manifest = json.loads(zipfile.ZipFile(path).read("manifest.json"))
        except (zipfile.BadZipFile, KeyError, ValueError) as exc:
            refuse("bundle has no readable manifest.json (%s)" % exc)
        if manifest.get("track") != "experimental" or manifest.get("version") != version:
            refuse("bundle manifest says %s %s" % (manifest.get("track"), manifest.get("version")))

        if home_asset is not None:
            with open(os.devnull, "wb") as sink:
                same, _, _ = download_asset(HOME, home_asset["id"], sink, data.get("size"), data.get("sha256"))
            if not same:
                refuse("%s already holds %s with other bytes under %s" % (HOME, asset_name, tag))
        else:
            named = os.path.join(os.path.dirname(path), asset_name)
            os.replace(path, named)
            path = named
            title = "%s (%s)" % (re.split(r"[;.]", data.get("notes") or "")[0].strip()[:80] or "Experimental build",
                                 version)
            notes = "%s\n\nPick Experimental Build in ScdaLauncher.exe and press PLAY.\n\nPublished from %s." % (
                data.get("notes", ""), SOURCE)
            if home_rel is None:
                gh("release", "create", tag, path, "--repo", HOME, "--prerelease", "--title", title, "--notes", notes)
            else:
                if not home_rel.get("prerelease"):
                    refuse("%s exists in %s but is not a pre-release" % (tag, HOME))
                gh("release", "upload", tag, path, "--repo", HOME)
            check = next((a for a in (release(HOME, tag) or {}).get("assets", []) if a["name"] == asset_name), None)
            if check is None or check["size"] != data.get("size"):
                refuse("the copy in %s did not land with the right size" % HOME)
    finally:
        if os.path.isfile(path):
            os.remove(path)

    data["bundle_url"] = "https://github.com/%s/releases/download/%s/%s" % (HOME, tag, asset_name)
    with open("latest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    git = lambda *a: subprocess.run(["git"] + list(a), check=True)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", "latest.json")
    git("commit", "-m", "Experimental branch: %s (mirrored from %s)\n\n%s" % (version, SOURCE, data.get("notes", "")))
    git("push", "origin", "HEAD:experimental")
    summary(":white_check_mark: experimental channel now %s" % version)


if __name__ == "__main__":
    main()
