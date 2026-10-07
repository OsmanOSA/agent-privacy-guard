"""Constant PowerShell/WPF renderer; JSON display fields arrive through stdin."""

import base64

from privacy_guard.notifications.card_layout import CARD_XAML

READY = "PRIVACY_GUARD_CARD_READY"
PREPARED = "PRIVACY_GUARD_CARD_PREPARED:"
CLICKED = "PRIVACY_GUARD_CARD_CLICKED"


def encoded_script():
    layout = base64.b64encode(CARD_XAML.encode("utf-8")).decode("ascii")
    source = "\n".join([
        "$ErrorActionPreference='Stop'",
        "[Console]::InputEncoding=[Text.Encoding]::UTF8",
        "$payload=[Console]::In.ReadLine()|ConvertFrom-Json",
        "Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase",
        # A user click lets this child grant foreground permission to its parent.
        "Add-Type 'using System; using System.Runtime.InteropServices; public static class CardNative { [DllImport(\"user32.dll\")] public static extern bool AllowSetForegroundWindow(uint pid); }'",
        f"$xaml=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{layout}'))",
        "$reader=New-Object System.Xml.XmlNodeReader ([xml]$xaml)",
        "$window=[Windows.Markup.XamlReader]::Load($reader)",
        "foreach($pair in @(@('Headline','headline'),@('Document','document'),@('Details','details'),@('Footer','footer'))){",
        " $window.FindName($pair[0]).Text=[string]$payload.($pair[1])",
        "}",
        # Static-image QA uses the same control tree without showing a desktop window.
        "if($payload.preview){",
        " $card=$window.FindName('Card');$window.Content=$null;$card.Resources=$window.Resources",
        " $card.Measure((New-Object Windows.Size(412,[double]::PositiveInfinity)))",
        " $card.Arrange((New-Object Windows.Rect(0,0,412,$card.DesiredSize.Height)));$card.UpdateLayout()",
        " $bitmap=New-Object Windows.Media.Imaging.RenderTargetBitmap(412,[int][Math]::Ceiling($card.DesiredSize.Height),96,96,[Windows.Media.PixelFormats]::Pbgra32)",
        " $bitmap.Render($card);$encoder=New-Object Windows.Media.Imaging.PngBitmapEncoder",
        " $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))",
        " $file=[IO.File]::Create([string]$payload.preview);try{$encoder.Save($file)}finally{$file.Dispose()}",
        " exit 0",
        "}",
        # Window.DesiredSize can still be only its chrome before first display.
        # Measure the actual card, including its margins, while keeping it hidden.
        "$card=$window.FindName('Card');$card.Measure((New-Object Windows.Size(412,[double]::PositiveInfinity)))",
        "$window.Height=[Math]::Min(420,[Math]::Max(180,$card.DesiredSize.Height));$window.SizeToContent=[Windows.SizeToContent]::Manual",
        "$handle=(New-Object Windows.Interop.WindowInteropHelper($window)).EnsureHandle()",
        "[Console]::Out.WriteLine('" + PREPARED + "'+$handle.ToInt64());[Console]::Out.Flush()",
        "$permit=[Console]::In.ReadLine()|ConvertFrom-Json;if(-not $permit.show){exit 0}",
        "if($permit.can_return){$window.FindName('Return').Visibility=[Windows.Visibility]::Visible}",
        "$window.FindName('Return').Add_Click({$null=[CardNative]::AllowSetForegroundWindow([uint32]$payload.return_pid);[Console]::Out.WriteLine('" + CLICKED + "');[Console]::Out.Flush();$window.Close()})",
        "$window.FindName('Close').Add_Click({$window.Close()})",
        "$window.Add_KeyDown({if($_.Key -eq [Windows.Input.Key]::Escape){$window.Close()}})",
        "$started=[DateTime]::UtcNow;$timer=New-Object Windows.Threading.DispatcherTimer",
        "$timer.Interval=[TimeSpan]::FromMilliseconds(250)",
        "$timer.Add_Tick({$elapsed=([DateTime]::UtcNow-$started).TotalSeconds;if($elapsed -ge 60 -or ($elapsed -ge 10 -and -not $window.IsMouseOver)){$window.Close()}})",
        "$timer.Start();$app=New-Object Windows.Application",
        "$app.ShutdownMode=[Windows.ShutdownMode]::OnExplicitShutdown",
        "$window.Add_ContentRendered({[Console]::Out.WriteLine('" + READY + "');[Console]::Out.Flush()})",
        "$window.Add_Closed({$timer.Stop();$app.Shutdown()})",
        "$null=$app.Run($window)",
    ])
    return base64.b64encode(source.encode("utf-16-le")).decode("ascii")
