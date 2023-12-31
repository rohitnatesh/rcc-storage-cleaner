import os
import sys
import argparse
import subprocess
import datetime


time_mapping = {"access": "st_atime", "change": "st_ctime", "modified": "st_mtime"}


def get_storage_information(args):
    directory_path = args.directory_path
    storage_ssh_host = args.storage_ssh_host
    storage_quota_command = args.storage_quota_command
    storage_block_size = args.storage_block_size
    storage_fileset = args.storage_fileset
    storage_post_process = args.storage_post_process
    storage_custom_command = args.storage_custom_command

    if storage_custom_command:
        command = storage_custom_command
    else:
        if storage_fileset:
            fileset = storage_fileset
        else:
            fileset = directory_path.replace("\\", "/").split("/")
            fileset = " ".join(fileset[1:])

        command = f"ssh {storage_ssh_host} {storage_quota_command} --block-size={storage_block_size} -j {fileset}"
        command = (
            f"{command} | {storage_post_process}" if storage_post_process else command
        )

    storage_information = subprocess.check_output(
        command,
        shell=True,
        text=True,
        stderr=sys.stderr,
    ).strip()

    return storage_information


def iterate_and_delete(
    paths, root, time_attribute, delete_older_than, dry_run, is_directory=False
):
    directories_to_delete = []

    for path in paths:
        full_path = os.path.join(root, path)
        file_stat = os.stat(full_path)
        current_time_attr = getattr(file_stat, time_mapping[time_attribute])
        file_age_days = (
            datetime.datetime.now() - datetime.datetime.fromtimestamp(current_time_attr)
        ).days

        if file_age_days >= delete_older_than:
            if is_directory:
                directories_to_delete.append(full_path)
            else:
                print(f"Deleting: {full_path}")

                if not dry_run:
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        print(e, file=sys.stderr)

    return directories_to_delete if is_directory else None


def main(args):
    dry_run = args.dry_run
    directory_path = args.directory_path
    delete_older_than = args.delete_older_than
    time_attribute = args.time_attribute

    print(
        f"{datetime.datetime.now()} - start: will clean out data older than {delete_older_than} days in {directory_path}"
    )

    before_clean = get_storage_information(args)

    directories_to_delete = []

    for root, directories, files in os.walk(directory_path):
        iterate_and_delete(files, root, time_attribute, delete_older_than, dry_run)

        if directories:
            new_directories_to_delete = iterate_and_delete(
                directories, root, time_attribute, delete_older_than, dry_run, True
            )
            directories_to_delete.extend(new_directories_to_delete)

    for directory in directories_to_delete:
        print(f"Deleting: {directory}")

        if not dry_run:
            try:
                os.rmdir(directory)
            except Exception as e:
                print(e, file=sys.stderr)

    after_clean = get_storage_information(args)

    print(
        f"{datetime.datetime.now()} - finish: before cleanup ({before_clean}) --- after cleanup: ({after_clean})"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deletes old files and directories from directory."
    )
    parser.add_argument(
        "directory_path", type=str, help="Directory to traverse for old files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lists the old files and directories without actually deleting them.",
    )
    parser.add_argument(
        "--delete-older-than",
        "-d",
        type=int,
        default=90,
        help="Delete files older than specified days.",
    )
    parser.add_argument(
        "--time-attribute",
        "-t",
        choices=["access", "change", "modified"],
        default="access",
        help="Choose time attribute for file age calculation.",
    )
    parser.add_argument(
        "--storage-ssh-host",
        "-sh",
        type=str,
        default="n22-gpfs-quorum",
        help="SSH host to connect and query storage information. Is not used when custom storage command is provided.",
    )
    parser.add_argument(
        "--storage-quota-command",
        "-qc",
        type=str,
        default="/usr/lpp/mmfs/bin/mmlsquota",
        help="Command used to query storage information. Is not used when custom storage command is provided.",
    )
    parser.add_argument(
        "--storage-block-size",
        "-bs",
        type=str,
        default="auto",
        help="The unit in which the number of storage blocks is displayed. Is not used when custom storage command is provided.",
    )
    parser.add_argument(
        "--storage-volume",
        "-j",
        type=str,
        help="The storage fileset to use. By default, it is derived from the deletion directory information. Is not used when custom storage command is provided.",
    )
    parser.add_argument(
        "--storage-post-process",
        "-pp",
        type=str,
        default="tail -n 1 | awk '{ print $3 }'",
        help="Post-processing steps after storage information is collected. Is not used when custom storage command is provided.",
    )
    parser.add_argument(
        "--storage-custom-command",
        type=str,
        help="Post-processing steps after storage information is collected. When the custom storage command is provided, none of the other storage arguments will be used.",
    )

    try:
        args = parser.parse_args()
        main(args)
    except Exception as e:
        print(e, file=sys.stderr)
