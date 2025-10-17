# State-Archives-Transcription

_An app for OCR-based transcription of scanned, handwritten archives._

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Docker Build](https://img.shields.io/docker/cloud/build/your-repo/state-archives-transcription)]

---

## Table of Contents
- [State-Archives-Transcription](#state-archives-transcription)
  - [Table of Contents](#table-of-contents)
  - [Releases](#releases)
    - [For Developers – Creating a New Release](#for-developers--creating-a-new-release)
    - [For Users – Installing the App](#for-users--installing-the-app)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Getting Started](#getting-started)
    - [Clone](#clone)
    - [Docker](#docker)
    - [Quick Start (Subsequent Runs)](#quick-start-subsequent-runs)
  - [Usage](#usage)
  - [Project Structure](#project-structure)
  - [Contributing](#contributing)
  - [License](#license)

---

## Releases

### For Developers – Creating a New Release

1. Make sure your changes are committed and pushed to the `windows-installer` branch.
2. Update the version number if needed (e.g. `v1.1.0`).
3. Create and push a new tag to trigger the build:

   ```bash
   git checkout windows-installer
   git pull
   git tag -a v1.1.0 -m "Release v1.1.0"
   git push origin v1.1.0
   ```
4. GitHub Actions will automatically build the Windows installer and upload it to the **Releases** page.

### For Users – Installing the App

1. Go to the project’s [**Releases**](../../releases/latest) page.
2. Download the latest file named **`StateArchivesTranscription-Setup.exe`**.
3. Run the installer and follow the prompts.

   - You can optionally enter your **Google AI API Key** for Gemini.
   - A desktop shortcut will be created automatically.

4. After installation, open the shortcut to launch the app in your browser.

---

## Features

- PDF -> images -> text via Microsoft TrOCR
- Simple web UI for uploading/downloading transcriptions
- Local database of transcribed files

## Prerequisites

- **Docker Desktop**

---

## Getting Started

### Clone

```bash
git clone https://github.com/ksermon/State-Archives-Transcription.git
cd State-Archives-Transcription
```

### Docker
From the project root run:
```bash
docker compose up --build
```
Open your browser at http://localhost:5000.

*Note:* The first build will download dependencies and model files, it will take much longer the first time. 

### Quick Start (Subsequent Runs)

From the project root again, since your image is already built, run:
```bash
docker compose up
```

## Usage

1. Upload a PDF or image
2. Wait for OCR processing (page will reload automatically when complete)
3. Copy the resulting plain-text ***[export text and JSON coming soon]***

## Project Structure
```bash
├── app/
│   ├── main/           # Flask blueprints (routes, errors, utils)
│   ├── models/         # SQLAlchemy ORM
│   └── utils/          # OCR engine, preprocessing
├── app/models/         # local TrOCR weights
└── entrypoint.sh       # container startup logic (DB init, etc.)
```

## Contributing
(for Keeley, by Keeley, I will remember this)
1. Add or find an issue
2. Create a branch (`git checkout -b feat/xyz)
3. Commit your changes (git commit -m "Add xyz")
4. Push and open a PR

## License

This project is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).  

See the full license text in the [LICENSE](LICENSE) file.
