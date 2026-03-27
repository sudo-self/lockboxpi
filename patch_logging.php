<?php
$file = '/var/www/dumps/receive_udid.php';
$content = file_get_contents($file);

$content = str_replace(
    "file_put_contents('enrollment_debug.log', \"Telegram notified successfully.\\n\", FILE_APPEND);",
    "file_put_contents('enrollment_debug.log', \"Telegram Response: \$result\\n\", FILE_APPEND);",
    $content
);

file_put_contents($file, $content);
echo "Patched logging";
