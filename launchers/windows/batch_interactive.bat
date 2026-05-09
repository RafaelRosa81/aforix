@echo off
REM Batch interactive launcher

call conda activate aforix

cd /d %~dp0\..\..\

cmd /k aforix batch interactive
