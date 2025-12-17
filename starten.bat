:: Speichere diese Datei in deinem Ordner "AktienApp"
:: Dann kannst du das Programm einfach per Doppelklick starten!

@echo off
title StockVision AI Starter
cd /d "%~dp0"
echo -------------------------------------------------------
echo Starte StockVision AI Pro...
echo Bitte warten, der Browser oeffnet sich gleich automatisch.
echo WICHTIG: Dieses schwarze Fenster muss offen bleiben!
echo -------------------------------------------------------
py -m streamlit run aktien_pro.py
pause

