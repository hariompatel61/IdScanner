# Testing Strategy

## Layers of Testing
1. **Unit Tests (Backend)**: Pytest for extraction logic, validation logic, config loading, and API endpoints.
2. **Unit Tests (Frontend)**: Vitest for React components, scanner state machine, and utility functions.
3. **Integration Tests (Backend)**: Testing the full OCR pipeline from image upload to validated result.
4. **Accuracy Benchmark**: A separate suite in `benchmark/` to measure P50/P95 latencies and OCR accuracy on a golden dataset.

## Running Tests (Phase 1)
- Backend: `cd backend && python -m pytest`
- Frontend: `cd frontend && npm run test`

*Note: Phase 1 configures the test runners and basic structural tests. Computer Vision tests will be added in later phases.*
