# English Vocabulary

## English vocabulary learning app for Russians

### Install dependencies from `requirements.txt`:

```
git clone https://github.com/o5b/...
cd ...
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install dependencies from `pyproject.toml`:

```
poetry install
```

### Run as a desktop app:

```
flet run
```

Or

```
poetry run flet run
```

## Build the app

### Android

```
cd ...
source venv/bin/activate
pip cache purge
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

## Implemented functionality

### Learning English words

[![English vocabulary learning app for Russians - Training](https://img.youtube.com/vi/ZgoFXtf87-I/0.jpg)](https://www.youtube-nocookie.com/embed/ZgoFXtf87-I)

### Create a dictionary from selected words

[![English vocabulary learning app for Russians - Dictionary](https://img.youtube.com/vi/J5LDpdsYlgA/0.jpg)](https://www.youtube-nocookie.com/embed/J5LDpdsYlgA)
