@echo off
rem Outfit review app: opens its own window; the server stops ~45 s after the window closes.
rem Usage: Review.cmd [batch folder]   (default: newest batch under E:\Felt\review)
python "%~dp0server.py" %*
