# PHP Example

This example uses standard cURL in PHP to safely upload the document and handle errors.

## Scan Document

```php
<?php

function scanDocument($filePath, $apiToken) {
    $url = "http://localhost:4500/api/v1/scan";
    
    if (!file_exists($filePath)) {
        die("File not found.");
    }

    $cfile = new CURLFile($filePath, 'image/jpeg', 'document.jpg');
    
    $postData = array(
        'file' => $cfile
    );

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    // Timeout handling
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        "Authorization: Bearer " . $apiToken,
        "X-Request-ID: req_php_1"
    ));

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        echo "cURL Error: $error\n";
        return;
    }

    if ($httpCode === 429) {
        echo "Error: Rate Limit Exceeded\n";
        return;
    }

    $data = json_decode($response, true);
    
    if (isset($data['success']) && $data['success']) {
        echo "Success! Document: " . $data['document_type'] . "\n";
        echo "Status: " . $data['status'] . "\n";
        print_r($data['fields']);
    } else {
        $msg = isset($data['error']['message']) ? $data['error']['message'] : "Unknown error";
        echo "Scan Failed: " . $msg . "\n";
    }
}

// Run
scanDocument("document.jpg", "test_token");
?>
```
