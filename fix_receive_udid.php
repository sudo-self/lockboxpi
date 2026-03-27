<?php
$file = '/var/www/dumps/receive_udid.php';
$content = file_get_contents($file);

// Replace parse_ini_file with a custom regex parser because parse_ini_file 
// breaks if the .env values contain special unquoted characters (like bot token colons) or if it's strictly not an INI
$newParser = <<<EOT
        \$envContent = file_get_contents(\$envPath);
        preg_match('/BOT_TOKEN=(.*)/', \$envContent, \$tokenMatch);
        preg_match('/ALLOWED_USERS=(.*)/', \$envContent, \$usersMatch);
        
        if (isset(\$tokenMatch[1]) && isset(\$usersMatch[1])) {
            \$botToken = trim(\$tokenMatch[1]);
            \$chatIds = explode(',', trim(\$usersMatch[1]));
EOT;

$content = preg_replace(
    '/\$envVars = parse_ini_file\(\$envPath\);\s*if \(isset\(\$envVars\[\'BOT_TOKEN\'\]\) && isset\(\$envVars\[\'ALLOWED_USERS\'\]\)\) \{\s*\$botToken = \$envVars\[\'BOT_TOKEN\'\];\s*\$chatIds = explode\(\',\', \$envVars\[\'ALLOWED_USERS\'\]\);/s',
    $newParser,
    $content
);

file_put_contents($file, $content);
echo "Patched parser";
