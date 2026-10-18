"""將建置環境中套件的原始授權文件附於 portable 產物。"""
from importlib.metadata import distributions
from pathlib import Path
import shutil

destination = Path('dist/Voice2Txt/THIRD_PARTY_LICENSES')
destination.mkdir(exist_ok=True)
for distribution in list(distributions()) + list(distributions(path=['gpu'])):
    name = distribution.metadata.get('Name', 'unknown')
    for file in distribution.files or []:
        if file.name.lower().startswith(('license', 'copying', 'copyright', 'notice')):
            source = distribution.locate_file(file)
            if not source.is_file():
                continue
            target = destination / name / file.name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
print(destination)
