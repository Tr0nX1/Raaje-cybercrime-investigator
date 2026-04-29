# Unstract PDF to JSON Engine Setup

## Steps
1. Run setup script: `bash unstract/run-platform.sh`
2. Verify services: `docker ps`
3. Backup ENCRYPTION_KEY from unstract/backend/.env
4. Configure LLM (Ollama or Mistral) in unstract/backend/.env
5. Restart backend: `cd unstract/docker && docker compose up -d backend`
6. Test auth API
7. Create prompt for bank statement extraction
8. Deploy as API
9. Test with PDF from bank_statement_analyzer/input files/
10. Integrate with project

Progress: Steps 1-5 complete (Docker pull/up running).
