@echo off
REM Create virtual environment
python -m venv venv

REM Activate virtual environment
call venv\Scripts\activate

REM Run the Streamlit app
streamlit run streamlit_ui.py
