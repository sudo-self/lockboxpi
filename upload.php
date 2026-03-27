<?php
// Settings
$targetDir = "/home/lockboxpi/dumps/";
$message = "";

// Ensure the directory exists
if (!file_exists($targetDir)) {
    mkdir($targetDir, 0775, true);
}

if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_FILES["fileToUpload"])) {
    $fileName = basename($_FILES["fileToUpload"]["name"]);
    $targetFilePath = $targetDir . $fileName;

    if (move_uploaded_file($_FILES["fileToUpload"]["tmp_name"], $targetFilePath)) {
        $message = "<div class='success'>✅ <b>$fileName</b> uploaded to /dumps</div>";
    } else {
        $error = error_get_last();
        $message = "<div class='error'>❌ Error: " . $error['message'] . " (Check permissions)</div>";
    }
}

// Get last 5 files in /dumps for verification
$files = array_diff(scandir($targetDir, SCANDIR_SORT_DESCENDING), array('..', '.'));
$recentFiles = array_slice($files, 0, 5);
?>

<!DOCTYPE html>
<html>
<head>
    <title>lockboxPRO | Uploader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, sans-serif; background: #121212; color: white; display: flex; justify-content: center; padding-top: 50px; }
        .card { background: #1e1e1e; padding: 25px; border-radius: 15px; width: 100%; max-width: 400px; border: 1px solid #333; }
        h2 { margin-top: 0; color: #007aff; }
        input[type="file"] { display: block; margin: 20px 0; width: 100%; color: #ccc; }
        input[type="submit"] { background: #007aff; color: white; border: none; padding: 12px; width: 100%; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .success { color: #4cd964; margin-top: 15px; }
        .error { color: #ff3b30; margin-top: 15px; }
        .file-list { margin-top: 30px; border-top: 1px solid #333; padding-top: 15px; font-size: 0.85rem; }
        .file-list ul { list-style: none; padding: 0; color: #888; }
    </style>
</head>
<body>
    <div class="card">
        <h2>lockboxPRO Drop</h2>
        <form action="" method="post" enctype="multipart/form-data">
            <input type="file" name="fileToUpload" required>
            <input type="submit" value="Upload to /dumps">
        </form>
        
        <?php echo $message; ?>

        <div class="file-list">
            <strong>Recent in /dumps:</strong>
            <ul>
                <?php foreach($recentFiles as $f): ?>
                    <li>📄 <?php echo $f; ?></li>
                <?php endforeach; ?>
            </ul>
        </div>
    </div>
</body>
</html>
