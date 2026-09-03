# Test Laboratory

The Test Laboratory encompasses the repeatable test suite that validates the ID Scanner. 
It integrates seamlessly with the Phase 8 benchmark runner.

## Core Commands

### Run Full Benchmark
Generate fresh synthetic fixtures and run the full pipeline test:
```bash
python scripts/generate_fixtures.py
python scripts/benchmark.py
```
*Note: This will execute all image conditions (clean, blur, glare, low_light, rotation) across all document plugins.*

### Run Existing Suite
```bash
pytest tests/ -v
```

## Regression Corpus
Any bugs discovered are converted into tests in `tests/test_real_images.py` or `tests/test_parsers.py` to prevent silent regressions. 

## Synthetic Data Generator
`scripts/generate_fixtures.py` handles the creation of varied synthetic documents using `OpenCV`. It generates standard configurations, varying image clarity and geometric perspective.
