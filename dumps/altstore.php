<?php
/**
 * lockboxPRO Profile Installer
 * Serving from: https://10.0.0.131:8443/dumps/altstore.php
 */

// 1. Set the specific Apple MIME type headers
header('Content-Type: application/x-apple-aspen-config');
header('Content-Disposition: attachment; filename="lockboxPRO.mobileconfig"');

// 2. Generate the Profile XML
// Note: The UUIDs are random. The URL is set to your Pi's dashboard.
$profileXML = <<<XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>FullScreen</key>
            <true/>
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>lockboxPRO</string>
            <key>PayloadDescription</key>
            <string>Configures Web Clip for lockboxPRO Dashboard</string>
            <key>PayloadDisplayName</key>
            <string>lockboxPRO Web Clip</string>
            <key>PayloadIdentifier</key>
            <string>com.jessejesse.lockbox.webclip</string>
            <key>PayloadType</key>
            <string>com.apple.webClip.managed</string>
            <key>PayloadUUID</key>
            <string>E9345678-C123-4567-B123-DDEEFF001122</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>URL</key>
            <string>https://10.0.0.131:8443/dumps/</string>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>lockboxPRO Setup</string>
    <key>PayloadIdentifier</key>
    <string>com.jessejesse.lockbox</string>
    <key>PayloadOrganization</key>
    <string>lockboxPRO</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>5F3B1A2C-9D4E-4A1B-8C2D-E3F4G5H6I7J8</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
XML;

// 3. Output the XML and exit
echo $profileXML;
exit;
?>
