@echo off
REM Scheduled entry point for Omar's Drive-to-website photo sync.
REM Registered as the Windows Scheduled Task "OmarSiteSync" (see scripts/omar_site_sync.py
REM header). Runs the sync and appends output to a rolling log so a failed run is
REM diagnosable after the fact. Keep this thin: all real logic lives in the .py.
cd /d "c:\Propcheck Git\clone\masters"
echo ==== %DATE% %TIME% ==== >> "c:\Propcheck Git\clone\masters\.secrets\omar_sync.log"
python "c:\Propcheck Git\clone\masters\scripts\omar_site_sync.py" >> "c:\Propcheck Git\clone\masters\.secrets\omar_sync.log" 2>&1
