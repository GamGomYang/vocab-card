# Vocab Card

## requirements

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
```

## Build 방법

Frontend production build:

```powershell
cd frontend
npm run build
```

Backend syntax check:

```powershell
cd backend
.\.venv\Scripts\python -m py_compile main.py excel_repository.py quiz_service.py test_api_loop.py
```
