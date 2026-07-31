@echo off
rem Morning runner for the Revolver News stories sweep.
rem Registered as scheduled task "RevolverNewsStories" (daily 07:30):
rem   schtasks /Create /TN "RevolverNewsStories" /SC DAILY /ST 07:30 /F ^
rem     /TR "\"c:\Propcheck Git\clone\masters\scripts\revolver_stories_task.cmd\""
rem Remove with: schtasks /Delete /TN "RevolverNewsStories" /F
cd /d "c:\Propcheck Git\clone\masters"
echo ================ %date% %time% ================>> revolver_stories.log
python scripts\revolver_stories.py >> revolver_stories.log 2>&1
