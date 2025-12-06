#!/bin/bash
echo "================================================="
echo "     Vision AI — Construction Safety Agent       "
echo "================================================="
echo "Backend  → http://localhost:8000"
echo "Frontend → http://localhost:8501"
echo "Close this terminal to stop"
echo

# Start backend in background
cd backend/app
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ../..

# Wait for backend
sleep 3

# Start frontend
cd frontend
streamlit run app.py --server.port 8501

# When frontend exits, kill backend
kill $BACKEND_PID 2>/dev/null