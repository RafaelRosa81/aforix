@echo off
REM Normalize interactive launcher

call conda activate aforix

cd /d %~dp0\..\..\

cmd /k aforix normalize interactive
