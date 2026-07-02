"""Vault skeleton bootstrap (v1.4.0 WS3, D29/D30).

Creates the EM Vault working layout under EM_VAULT_DIR (or --vault-dir):

    00_system/            the contract, copied from the repo (read-only reference)
    07_agent_workspaces/  ungoverned scratch - never scanned
    08_proposals/         the agent-finding return path (PROPOSAL-lane connector)

Folders 01-06 are reserved for the v1.5 EM Vault renderer and are
deliberately NOT created. Idempotent: re-running refreshes 00_system
from the repo and leaves agent-written content untouched. Standard
library only - the vault is scaffolding, never a governed subsystem.
"""
import argparse
import os
import shutil
import sys

REPO_SYSTEM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "00_system")
SKELETON = ("00_system", "07_agent_workspaces", "08_proposals")


def bootstrap(vault_dir: str) -> dict:
    summary = {"vault_dir": vault_dir, "created": [], "system_files": []}
    for folder in SKELETON:
        path = os.path.join(vault_dir, folder)
        if not os.path.isdir(path):
            os.makedirs(path)
            summary["created"].append(folder)
    for name in sorted(os.listdir(REPO_SYSTEM_DIR)):
        src = os.path.join(REPO_SYSTEM_DIR, name)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(vault_dir, "00_system", name))
            summary["system_files"].append(name)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create the EM Vault skeleton.")
    parser.add_argument("--vault-dir", default=os.environ.get("EM_VAULT_DIR"),
                        help="Target directory (default: EM_VAULT_DIR)")
    args = parser.parse_args(argv)
    if not args.vault_dir:
        print("No vault directory: set EM_VAULT_DIR or pass --vault-dir.")
        return 2
    summary = bootstrap(args.vault_dir)
    print(f"Vault skeleton at {summary['vault_dir']}: "
          f"created {summary['created'] or 'nothing (already present)'}, "
          f"00_system holds {summary['system_files']}. "
          f"Folders 01-06 are reserved for the v1.5 vault renderer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
