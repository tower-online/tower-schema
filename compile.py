import argparse
import os
import pathlib
import re
import subprocess

FLATC_URL_LINUX = "https://github.com/google/flatbuffers/releases/download/v24.3.25/Linux.flatc.binary.g++-13.zip"
FLATC_URL_WINDOWS = "https://github.com/google/flatbuffers/releases/download/v24.3.25/Windows.flatc.binary.zip"

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", required=True)
parser.add_argument("-i", "--input", required=True)
parser.add_argument("--lang", type=str, default="cpp")
parser.add_argument("--namespace-pascalcase", action="store_true", help="Set namespace as pascal case")
parser.add_argument("--download-flatc", action="store_true", help="Download flatc and use it")
parser.add_argument("--platform", type=str, default="linux")
# parser.add_argument("files", metavar='N', nargs='+', type=str)
args = parser.parse_args()


# Configure
files = pathlib.Path(args.input).rglob("*.fbs")
for input_file in files:
    path, filename = os.path.split(input_file)
    
    temp_path = os.path.join("temp", path)
    temp_file = os.path.join("temp", path, filename)

    os.makedirs(temp_path, exist_ok=True)

    with open(input_file, 'r') as src, open(temp_file, 'w') as dst:
        lines = src.readlines()

        if args.namespace_pascalcase:
            for i, line in enumerate(lines):
                m = re.match(r'^namespace ([^"]*);', line)
                if m:
                    pascalcased_namespace = '.'.join(word.capitalize() for word in m.group(1).split('.'))
                    lines[i] = f'namespace {pascalcased_namespace};\n'

        dst.write("".join(lines))


# Download flatc
if args.download_flatc:
    import stat
    from io import BytesIO
    from urllib.request import urlopen
    from zipfile import ZipFile

    os.makedirs("bin", exist_ok=True)

    if args.platform == "linux":
        url = FLATC_URL_LINUX
    elif args.platform == "windows":
        url = FLATC_URL_WINDOWS

    print(f"Downloading and extracting flatc from {url}...")
    resp = urlopen(url)
    file = ZipFile(BytesIO(resp.read()))
    file.extract("bin/flatc")

    # chmod +x
    st = os.stat("bin/flatc")
    os.chmod("bin/flatc", st.st_mode | stat.S_IEXEC )


# Compile schemas
schemas = pathlib.Path("temp").rglob("*.fbs")

flatc_args = ["./bin/flatc"]
if args.lang == "cpp":
    pass
elif args.lang == "csharp":
    flatc_args += ["--csharp", "--filename-suffix", '""', "-o", args.output, "-I", f"{os.path.join("temp", args.input)}"]
    flatc_args += [schema.as_posix() for schema in schemas]

print(flatc_args)
subprocess.run(flatc_args)

# Move out generated files from excessive namespace-path
if args.lang == "csharp":
    import shutil

    for file in pathlib.Path(os.path.join(args.output, *pascalcased_namespace.split("."))).glob("*"):
        target_file = os.path.join(args.output, os.path.basename(file))
        if os.path.exists(target_file):
            os.remove(target_file)

        shutil.move(file, args.output)
