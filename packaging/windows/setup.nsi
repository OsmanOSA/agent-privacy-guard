Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

!ifndef VERSION
  !error "Build with tools/build_windows_setup.py"
!endif
!ifdef TEST_BUILD
  !define PRODUCT "Privacy Guard Setup Test"
  !define DIRECTORY "PrivacyGuardSetupTest"
!else
  !define PRODUCT "Privacy Guard"
  !define DIRECTORY "PrivacyGuard"
!endif
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${DIRECTORY}"
!define BUNDLE "$INSTDIR\versions\${VERSION}"

Name "${PRODUCT} ${VERSION}"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\${DIRECTORY}"
InstallDirRegKey HKCU "${REGKEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor zlib
!include "lifecycle.nsh"
SetOverwrite on
ShowInstDetails show
ShowUninstDetails show

!define MUI_WELCOMEPAGE_TITLE "Installer ${PRODUCT}"
!define MUI_WELCOMEPAGE_TEXT "Ce setup installe Privacy Guard pour Claude Code sur ce compte Windows, avec Python et le modèle français inclus.$\r$\n$\r$\nFermez les sessions Claude Code avant de continuer. Claude Code doit déjà être installe (terminal ou extension VS Code).$\r$\n$\r$\nVersion de démonstration : détection imparfaite, couverture des outils encore en cours de validation. Notifications locales activées en arrière-plan lors d'une première installation."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TEXT "Privacy Guard est configuré pour ce compte Windows.$\r$\n$\r$\nOuvrez une nouvelle session Claude Code dans VS Code ou dans votre terminal. Aucune commande d'installation n'est nécessaire.$\r$\n$\r$\nLe menu Démarrer contient un raccourci pour verifier l'installation. Les documents scannés et l'OCR ne sont pas pris en charge."
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  Call AcquireSetupLock
  ${IfNot} ${IsNativeAMD64}
    MessageBox MB_ICONSTOP "Cette version nécessite Windows x64 (Intel/AMD)." /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "Windows 10 ou 11 est requis." /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
FunctionEnd

Section "Privacy Guard" SEC_MAIN
  Call CheckExistingVersion
  IfFileExists "${BUNDLE}\payload.json" activate
  SetOutPath "${BUNDLE}"
  File /r "${PAYLOAD}\*"
  activate:
  nsExec::ExecToStack /TIMEOUT=180000 '"${BUNDLE}\runtime\python.exe" -m privacy_guard.setup install --bundle "${BUNDLE}"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    DetailPrint "$1"
    StrCpy $1 "Installation incomplète.$\r$\n$1$\r$\nVos coffres existants sont conservés."
    Call SetupFailed
  ${EndIf}
  WriteINIStr "$INSTDIR\product.ini" "product" "id" "agent-privacy-guard"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${REGKEY}" "DisplayName" "${PRODUCT}"
  WriteRegStr HKCU "${REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher" "OsmanOSA"
  WriteRegStr HKCU "${REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "${REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REGKEY}" "NoRepair" 1
  CreateDirectory "$SMPROGRAMS\${DIRECTORY}"
  CreateShortcut "$SMPROGRAMS\${DIRECTORY}\Vérifier Privacy Guard.lnk" "${BUNDLE}\runtime\pythonw.exe" '-m privacy_guard.setup status --dialog'
  CreateShortcut "$SMPROGRAMS\${DIRECTORY}\Désinstaller.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  ReadINIStr $0 "$INSTDIR\product.ini" "product" "id"
  ${If} $0 != "agent-privacy-guard"
    MessageBox MB_ICONSTOP "Le dossier ne correspond pas a une installation Privacy Guard." /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
  nsExec::ExecToStack /TIMEOUT=90000 '"${BUNDLE}\runtime\python.exe" -m privacy_guard.setup uninstall --bundle "${BUNDLE}"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Désinstallation interrompue.$\r$\n$1" /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
  RMDir /r "${BUNDLE}"
  RMDir "$INSTDIR\versions"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$INSTDIR\product.ini"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\${DIRECTORY}\Vérifier Privacy Guard.lnk"
  Delete "$SMPROGRAMS\${DIRECTORY}\Désinstaller.lnk"
  RMDir "$SMPROGRAMS\${DIRECTORY}"
  DeleteRegKey HKCU "${REGKEY}"
SectionEnd
