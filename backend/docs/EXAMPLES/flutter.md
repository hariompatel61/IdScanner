# Flutter / Dart Example

This example uses the `http` package for multipart requests.

## Dependencies

```yaml
dependencies:
  http: ^1.1.0
```

## Scan Document

```dart
import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ScanResponse {
  final bool success;
  final String? documentType;
  final String? status;
  final Map<String, dynamic> fields;
  final String? errorMessage;

  ScanResponse({
    required this.success,
    this.documentType,
    this.status,
    required this.fields,
    this.errorMessage,
  });

  factory ScanResponse.fromJson(Map<String, dynamic> json) {
    return ScanResponse(
      success: json['success'] ?? false,
      documentType: json['document_type'],
      status: json['status'],
      fields: json['fields'] ?? {},
      errorMessage: json['error']?['message'] ?? json['message'],
    );
  }
}

Future<ScanResponse?> scanDocument(File imageFile, String apiToken) async {
  final uri = Uri.parse('http://10.0.2.2:4500/api/v1/scan'); // Localhost from Android emulator

  var request = http.MultipartRequest('POST', uri);
  
  request.headers.addAll({
    'Authorization': 'Bearer $apiToken',
    'X-Request-ID': 'req_flutter_1'
  });

  request.files.add(await http.MultipartFile.fromPath(
    'file',
    imageFile.path,
  ));

  try {
    // Implement timeout handling
    var streamedResponse = await request.send().timeout(const Duration(seconds: 15));
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 429) {
      print('Error: Rate Limit Exceeded');
      return null;
    }

    final data = jsonDecode(response.body);
    final scanRes = ScanResponse.fromJson(data);

    if (scanRes.success) {
      print('Success! Document: ${scanRes.documentType}');
      print('Status: ${scanRes.status}');
      print('Fields: ${scanRes.fields}');
    } else {
      print('Scan Failed: ${scanRes.errorMessage}');
    }

    return scanRes;
  } on TimeoutException {
    print('Error: Request timed out.');
    return null;
  } catch (e) {
    print('Unexpected error: $e');
    return null;
  }
}
```
