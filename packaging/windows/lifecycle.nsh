; One installer at a time, and immutable version directories.
Var SetupMutex

Function SetupFailed
  ; Persist local diagnostics even during a silent installation.
  FileOpen $9 "$TEMP\${DIRECTORY}-setup-error.txt" w
  FileWriteUTF16LE $9 "$1"
  FileClose $9
  MessageBox MB_ICONSTOP "$1" /SD IDOK
  SetErrorLevel 1
  Abort
FunctionEnd

Function AcquireSetupLock
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\${DIRECTORY}-Setup") p .r0 ?e'
  Pop $1
  StrCpy $SetupMutex $0
  ${If} $0 == 0
  ${OrIf} $1 == 183
    StrCpy $1 "Une installation Privacy Guard est déjà en cours."
    Call SetupFailed
  ${EndIf}
FunctionEnd

Function CheckExistingVersion
  ; Only an identical manifest may reuse this directory. Never overwrite an
  ; active runtime with different code under the same version number.
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=incoming.json "${PAYLOAD}\payload.json"
  IfFileExists "${BUNDLE}\*" 0 fresh
  IfFileExists "${BUNDLE}\payload.json" 0 mismatch
  FileOpen $2 "$PLUGINSDIR\incoming.json" r
  FileOpen $3 "${BUNDLE}\payload.json" r
  compare:
    ClearErrors
    FileRead $2 $4
    IfErrors finished
    FileRead $3 $5
    IfErrors different
    StrCmp $4 $5 compare different
  finished:
    ClearErrors
    FileRead $3 $5
    IfErrors identical different
  different:
    FileClose $2
    FileClose $3
    Goto mismatch
  identical:
    FileClose $2
    FileClose $3
    Return
  mismatch:
    StrCpy $1 "Ce numéro de version est déjà occupé par un autre build. Installez une version plus récente."
    Call SetupFailed
  fresh:
FunctionEnd
