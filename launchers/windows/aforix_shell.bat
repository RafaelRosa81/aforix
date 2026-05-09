@echo off
REM Aforix interactive shell launcher

call conda activate aforix

REM Open repository root
cd /d %~dp0\..\..\

cmd /k
