"""Small WPF card adapted from Driftlight's dark, document-first presentation.

Only layout is shared in spirit: the card is an informational renderer.
Runtime text is assigned to TextBlocks, never inserted into XAML or scripts.
"""

CARD_XAML = '''<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="Privacy Guard" Width="412"
 SizeToContent="Height" MaxHeight="420" WindowStyle="None" AllowsTransparency="True"
 Background="Transparent" ResizeMode="NoResize" ShowInTaskbar="False" ShowActivated="False"
 Topmost="True" UseLayoutRounding="True" FontFamily="Segoe UI">
 <Window.Resources>
  <Style TargetType="{x:Type Button}">
   <Setter Property="Template">
    <Setter.Value>
     <ControlTemplate TargetType="{x:Type Button}">
      <Border x:Name="ButtonSurface" Background="{TemplateBinding Background}" CornerRadius="5"
       BorderBrush="Transparent" BorderThickness="1" Padding="{TemplateBinding Padding}">
       <ContentPresenter x:Name="ButtonLabel" HorizontalAlignment="Center" VerticalAlignment="Center"
        RecognizesAccessKey="True" TextElement.Foreground="{TemplateBinding Foreground}"/>
      </Border>
      <ControlTemplate.Triggers>
       <Trigger Property="IsMouseOver" Value="True">
        <Setter TargetName="ButtonSurface" Property="Background" Value="#293E48"/>
        <Setter TargetName="ButtonLabel" Property="TextElement.Foreground" Value="#F3FBFF"/>
       </Trigger>
       <Trigger Property="IsPressed" Value="True">
        <Setter TargetName="ButtonSurface" Property="Background" Value="#204D4C"/>
        <Setter TargetName="ButtonLabel" Property="TextElement.Foreground" Value="#FFFFFF"/>
       </Trigger>
       <Trigger Property="IsKeyboardFocused" Value="True">
        <Setter TargetName="ButtonSurface" Property="BorderBrush" Value="#68DCCA"/>
       </Trigger>
      </ControlTemplate.Triggers>
     </ControlTemplate>
    </Setter.Value>
   </Setter>
  </Style>
 </Window.Resources>
 <Border x:Name="Card" Margin="12" CornerRadius="14" BorderThickness="1" BorderBrush="#495365" Padding="18,16">
  <Border.Background><LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
   <GradientStop Color="#242A35" Offset="0"/><GradientStop Color="#161C26" Offset="1"/>
  </LinearGradientBrush></Border.Background>
  <Border.Effect><DropShadowEffect BlurRadius="20" ShadowDepth="4" Opacity="0.45"/></Border.Effect>
  <StackPanel>
   <Grid>
    <Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/><ColumnDefinition Width="28"/></Grid.ColumnDefinitions>
    <Viewbox Width="20" Height="22" Margin="0,0,9,0">
     <Path Fill="#68DCCA" Data="M8,1 L15,4 L14,10 Q13,14 8,17 Q3,14 2,10 L1,4 Z"/>
    </Viewbox>
    <TextBlock Grid.Column="1" Text="Privacy Guard" Foreground="#ADB9CC" FontSize="12" FontWeight="SemiBold" VerticalAlignment="Center"/>
    <Button x:Name="Close" Grid.Column="2" Content="×" Background="Transparent" BorderThickness="0"
     Foreground="#BBC5D3" FontSize="20" Cursor="Hand" AutomationProperties.Name="Fermer la notification"/>
   </Grid>
   <TextBlock x:Name="Headline" Margin="0,12,0,0" Foreground="#F2F5FA" FontSize="17"
    FontWeight="SemiBold" TextWrapping="Wrap"/>
   <Border Margin="0,12,0,0" CornerRadius="8" Background="#101620" BorderBrush="#303B4B" BorderThickness="1" Padding="11,9">
    <TextBlock x:Name="Document" Foreground="#C4D4E8" FontFamily="Cascadia Mono, Consolas"
     FontSize="12" TextTrimming="CharacterEllipsis"/>
   </Border>
   <TextBlock x:Name="Details" Margin="0,12,0,0" Foreground="#DDE5F0" FontSize="13"
    TextWrapping="Wrap" MaxHeight="156" TextTrimming="CharacterEllipsis"/>
   <Border Height="1" Margin="0,14,0,0" Background="#354153"/>
   <Grid Margin="0,10,0,0">
    <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
    <TextBlock x:Name="Footer" Foreground="#94A4BA" FontSize="11" VerticalAlignment="Center"/>
    <Button x:Name="Return" Grid.Column="1" Visibility="Hidden" Content="Revenir à la fenêtre"
     Foreground="#68DCCA" Background="Transparent" BorderThickness="0" Padding="4,2" Cursor="Hand"/>
   </Grid>
  </StackPanel>
 </Border>
</Window>'''
