# State-Archives-Transcription

_An app for OCR-based transcription of scanned, handwritten archives._

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Docker Build](https://img.shields.io/docker/cloud/build/your-repo/state-archives-transcription)]

---

## Table of Contents
1. [Features](#features)  
2. [Prerequisites](#prerequisites)  
3. [Getting Started](#getting-started)  
   - [Clone](#clone)  
   - [Docker](#docker)  
   - [Quickstart](#quickstart)  
4. [Usage](#usage)  
5. [Project Structure](#project-structure)
6. [Contributing](#contributing)  
7. [License](#license) 

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
