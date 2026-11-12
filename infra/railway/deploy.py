#!/usr/bin/env python3
"""Create, update or check the hosted BLT on Railway.

  infra/railway/deploy.py            create or update: project, services, volume, domains, variables
  infra/railway/deploy.py --dry-run  print what it would do; change nothing
  infra/railway/deploy.py --check    compare this folder with what runs on Railway; change nothing

What runs is described by this folder: services.json (which directory each service is built from,
its variable files, settings, public port) and the *.env files (the non-secret variables, with
references such as ${{Postgres.PGHOST}}). Secrets are not in them: they go to Railway on stdin,
never as arguments.

Railway has deprecated railway.toml ("Config as Code"): services created after that cannot use it,
so the settings live here instead. Needs the Railway CLI, logged in (`railway login`), and these
git-ignored files: secrets/blt_password and secrets/opencode_api_key (override the second with
OPENCODE_API_KEY_FILE).
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.chdir(ROOT)

MANIFEST = json.loads((HERE / "services.json").read_text())
PROJECT = MANIFEST["project"]
ENVIRONMENT = MANIFEST["environment"]
SERVICES = MANIFEST["services"]
KEY_FILE = Path(os.environ.get("OPENCODE_API_KEY_FILE", "secrets/opencode_api_key"))
ENUM_SETTINGS = {"restartPolicyType"}  # GraphQL enums are written without quotes

DRY = False


def say(text):
    print(f"\n== {text}")


def railway(*args, stdin=None, mutates=True):
    """Run the Railway CLI. In a dry run, anything that changes state is only printed."""
    if DRY and mutates:
        print("  [dry-run] railway " + " ".join(args))
        return ""
    result = subprocess.run(["railway", *args], input=stdin, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
        raise SystemExit(f"railway {' '.join(args[:3])} failed: {detail[0][:200]}")
    return result.stdout


# ---------------------------------------------------------------- reading the project
def status():
    return json.loads(railway("status", "--json", mutates=False))


def instances():
    node = status()["environments"]["edges"][0]["node"]
    return node["id"], {
        s["node"]["serviceName"]: s["node"]["serviceId"] for s in node["serviceInstances"]["edges"]
    }


def live_variable_names(service):
    out = railway("variables", "-s", service, "--json", mutates=False)
    return set(json.loads(out))


def live_config():
    env_id, ids = instances()
    query = f'query {{ environment(id: "{env_id}") {{ config(decryptVariables: true) }} }}'
    cfg = json.loads(railway("api", query, mutates=False))["data"]["environment"]["config"]
    return {name: cfg["services"].get(sid, {}) for name, sid in ids.items()}


# ---------------------------------------------------------------- what this folder says
def parse_env(name):
    values = {}
    for line in (HERE / name).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def wanted_variables(service):
    merged = {}
    for name in SERVICES[service].get("variables", []):
        merged.update(parse_env(name))
    return merged


def password():
    return Path("secrets/blt_password").read_text().strip()


def secret_value(name):
    """The value of a secret, or None to leave the one on Railway as it is."""
    if name == "BLT_PASSWORD":
        return password()
    if name == "MP_UI_AUTH":
        return f"blt:{password()}"
    if name == "OPENCODE_API_KEY":
        return KEY_FILE.read_text().strip()
    if name == "DJANGO_SECRET_KEY":
        # Only when there is none, so running this again does not log everyone out.
        return (
            None if "DJANGO_SECRET_KEY" in live_variable_names("api") else secrets.token_urlsafe(48)
        )
    raise SystemExit(f"no source for the secret {name}")


# ---------------------------------------------------------------- check
def check():
    config = live_config()
    problems = []

    def problem(service, text):
        problems.append(f"  {service}: {text}")

    for service, spec in SERVICES.items():
        live = config.get(service)
        if live is None:
            problem(service, "does not exist on Railway")
            continue
        have = {k: v.get("value") for k, v in (live.get("variables") or {}).items()}
        want = wanted_variables(service)
        secret_names = set(spec.get("secrets", []))
        for key, value in want.items():
            if key not in have:
                problem(service, f"variable {key} is missing on Railway")
            elif have[key] != value:
                problem(service, f"variable {key} differs from {spec['variables']}")
        for key in secret_names - set(have):
            problem(service, f"secret {key} is not set on Railway")
        for key in set(have) - set(want) - secret_names:
            problem(service, f"variable {key} is on Railway but in no file here")
        deploy = live.get("deploy") or {}
        for key, value in spec.get("settings", {}).items():
            if deploy.get(key) != value:
                problem(service, f"setting {key} is {deploy.get(key)!r} on Railway, {value!r} here")
        if deploy.get("preDeployCommand"):
            problem(service, "a pre-deploy command is set (a one-off that was not cleared)")
        if spec.get("image") and (live.get("source") or {}).get("image") != spec["image"]:
            problem(service, f"image is not {spec['image']}")
        if spec.get("volume") and not any(
            m.get("mountPath") == spec["volume"] for m in (live.get("volumeMounts") or {}).values()
        ):
            problem(service, f"no volume mounted on {spec['volume']}")
        if spec.get("domain_port") and not live.get("networking"):
            problem(service, "has no public domain")
    for name in MANIFEST["databases"]:
        if name not in config:
            problem(name, "does not exist on Railway")
    if problems:
        print("Railway does not match infra/railway:")
        print("\n".join(problems))
        return 1
    databases = len(MANIFEST["databases"])
    print(f"Railway matches infra/railway: {len(SERVICES)} services and {databases} databases.")
    return 0


# ---------------------------------------------------------------- apply
def graphql_settings(service_id, env_id, settings):
    fields = ", ".join(
        f"{k}: {v}" if k in ENUM_SETTINGS else f"{k}: {json.dumps(v)}" for k, v in settings.items()
    )
    target = f'serviceId: "{service_id}", environmentId: "{env_id}"'
    return f"mutation {{ serviceInstanceUpdate({target}, input: {{ {fields} }}) }}"


def apply():
    if not Path("secrets/blt_password").is_file() or not KEY_FILE.is_file():
        raise SystemExit(
            f"secrets/blt_password and {KEY_FILE} are needed (the key is the AI provider's)."
        )

    say(f"Project {PROJECT}")
    try:
        linked = status().get("name") == PROJECT
    except SystemExit:
        linked = False
    if linked:
        print("  linked")
    elif subprocess.run(["railway", "link", "-p", PROJECT], capture_output=True).returncode == 0:
        print("  linked to the existing project")
    else:
        railway("init", "-n", PROJECT)

    say("Services")
    _, ids = instances() if not DRY or linked else (None, {})
    for name, kind in MANIFEST["databases"].items():
        if name not in ids:
            railway("add", "-d", kind)
    for name in SERVICES:
        if name not in ids:
            railway("add", "-s", name)

    say("Public domains (the API stays private behind nginx) and the volume")
    for name, spec in SERVICES.items():
        if spec.get("domain_port") and "RAILWAY_PUBLIC_DOMAIN" not in live_variable_names(name):
            railway("domain", "-s", name, "-p", str(spec["domain_port"]))
        if spec.get("volume"):
            volumes = json.loads(railway("volume", "list", "--json", mutates=False) or "[]")
            volumes = volumes if isinstance(volumes, list) else volumes.get("volumes", [])
            if not any(v.get("serviceName") == name for v in volumes):
                railway("service", "link", name)
                railway("volume", "add", "-m", spec["volume"])

    say("Variables")
    for name, spec in SERVICES.items():
        values = wanted_variables(name)
        railway(
            "variable",
            "set",
            "-s",
            name,
            "--skip-deploys",
            *[f"{k}={v}" for k, v in values.items()],
        )
        print(f"  {name}: {len(values)} set")
        for secret in spec.get("secrets", []):
            value = secret_value(secret)
            if value is None:
                print(f"  {name}: {secret} kept")
            else:
                railway(
                    "variable", "set", secret, "--stdin", "-s", name, "--skip-deploys", stdin=value
                )
                print(f"  {name}: {secret} set (stdin)")

    say("Service settings (the CLI cannot set these; the GraphQL API can)")
    if not DRY:
        env_id, ids = instances()
        for name, spec in SERVICES.items():
            if spec.get("settings"):
                railway("api", graphql_settings(ids[name], env_id, spec["settings"]))
                print(f"  {name}: {spec['settings']}")
            if (
                spec.get("image")
                and (live_config()[name].get("source") or {}).get("image") != spec["image"]
            ):
                railway("service", "source", "connect", "--image", spec["image"], "-s", name)
                print(f"  {name}: image {spec['image']}")
    else:
        print("  [dry-run] healthcheck, restart policy and image, as in services.json")

    say("Deploys: gitea and api first; web and the rest once api is up, so API_UPSTREAM resolves")
    for step in MANIFEST["deploy_order"]:
        if isinstance(step, str) and step.startswith("wait:"):
            wait_for(step.split(":", 1)[1])
            continue
        for name in step:
            if SERVICES[name].get("dir"):
                railway(
                    "up",
                    SERVICES[name]["dir"],
                    "--path-as-root",
                    "-s",
                    name,
                    "-e",
                    ENVIRONMENT,
                    "-d",
                    "-m",
                    "infra/railway/deploy.py",
                )
                print(f"  {name}: deploying from {SERVICES[name]['dir']}")

    say("Done")
    for name in ("web", "gitea", "mailpit"):
        if DRY:
            break
        out = json.loads(railway("variables", "-s", name, "--json", mutates=False))
        if out.get("RAILWAY_PUBLIC_DOMAIN"):
            print(f"  {name:8} https://{out['RAILWAY_PUBLIC_DOMAIN']}")
    print("  Users: fernando, ballast, lane (password: secrets/blt_password). Gitea: blt@mail.com")


def wait_for(name):
    if DRY:
        print(f"  [dry-run] wait for {name} (migrations and the seed run when it starts)")
        return
    print(f"  waiting for {name} (migrations and the seed run when it starts)...")
    for _ in range(60):
        for line in railway("service", "status", "--all", mutates=False).splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3 and parts[0] == name:
                if parts[2] == "SUCCESS":
                    return
                if parts[2] in ("FAILED", "CRASHED"):
                    raise SystemExit(f"{name} {parts[2]}: railway service logs -s {name}")
        time.sleep(15)
    raise SystemExit(f"{name} did not become healthy in 15 minutes")


def main():
    global DRY
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true", help="print what would be done")
    parser.add_argument("--check", action="store_true", help="compare this folder with Railway")
    args = parser.parse_args()
    DRY = args.dry_run
    if subprocess.run(["railway", "whoami"], capture_output=True).returncode != 0:
        raise SystemExit("Install the Railway CLI and run 'railway login' first.")
    sys.exit(check() if args.check else apply())


if __name__ == "__main__":
    main()
