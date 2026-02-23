# KB 금융그룹 Brand Color Guide

## Brand Identity

KB 금융그룹의 브랜드 아이덴티티는 두 가지 주요 색상으로 구성됩니다:
- **KB Yellow** (노란색)
- **KB Gray** (회색)

---

## Main Colors (주요 색상)

### 1. KB Yellow Positive
- **Pantone**: 130 C
- **CMYK**: C0 M35 Y100 K0
- **RGB**: R255 G188 B0
- **3M Sheet**: VT 10891

### 2. KB Yellow Negative
- **Pantone**: 1235 C
- **CMYK**: C0 M27 Y100 K0
- **RGB**: R255 G204 B0
- **3M Sheet**: VT 10801

### 3. KB Gray
- **Pantone**: 404 C
- **CMYK**: C0 M10 Y20 K65
- **RGB**: R96 G88 B76
- **3M Sheets**: 
  - VTB 11148
  - 5M VTB 11107 (윈도대형용)

---

## Sub Colors (보조 색상)

### 1. KB Dark Gray
- **Pantone**: 411C
- **CMYK**: C70 M65 Y75 K25
- **RGB**: R84 G80 B69
- **LG Sheet**: 하우시스_LB9706KB
- **Alternative**: 도씨샵 경우 노루표 페인트 DA056

### 2. KB Gold
- **Pantone**: 872 C
- **CMYK**: (금색 - 메탈릭)
- **3M Sheet**: Gold Metallic 3660-121

### 3. KB Silver
- **Pantone**: 877 C
- **CMYK**: (은색 - 메탈릭)
- **3M Sheet**: Silver 3650-121

---

## Color Usage Notes

### Primary Applications
- **KB Yellow**: 브랜드의 주요 식별 색상, 긍정적이고 활기찬 이미지
- **KB Gray**: 안정감과 신뢰감을 표현하는 보조 색상

### Material Specifications
- **3M Vinyl**: 대부분의 색상에 3M VT 또는 VTB 시트 사용
- **LG Hausys**: 다크 그레이의 경우 LG하우시스 제품 사용 가능
- **Paint Alternative**: 도씨샵의 경우 노루표 페인트 DA056 사용 가능

### Color Types
- **Positive/Negative**: KB Yellow는 포지티브와 네거티브 두 가지 버전 제공
- **Metallic**: 골드와 실버는 메탈릭 효과가 있는 특수 색상

---

## Implementation Guide for Claude Code

### Color Variables (RGB)
```
KB_YELLOW_POSITIVE = (255, 188, 0)
KB_YELLOW_NEGATIVE = (255, 204, 0)
KB_GRAY = (96, 88, 76)
KB_DARK_GRAY = (84, 80, 69)
```

### Color Variables (HEX)
```
KB_YELLOW_POSITIVE = #FFBC00
KB_YELLOW_NEGATIVE = #FFCC00
KB_GRAY = #60584C
KB_DARK_GRAY = #545045
```

### CMYK for Print
```
KB_YELLOW_POSITIVE: cmyk(0%, 35%, 100%, 0%)
KB_YELLOW_NEGATIVE: cmyk(0%, 27%, 100%, 0%)
KB_GRAY: cmyk(0%, 10%, 20%, 65%)
KB_DARK_GRAY: cmyk(70%, 65%, 75%, 25%)
```

---

## Quick Reference Table

| Color Name | RGB | HEX | Pantone | Primary Use |
|------------|-----|-----|---------|-------------|
| KB Yellow Positive | 255, 188, 0 | #FFBC00 | 130 C | Main brand color |
| KB Yellow Negative | 255, 204, 0 | #FFCC00 | 1235 C | Alternative yellow |
| KB Gray | 96, 88, 76 | #60584C | 404 C | Secondary brand color |
| KB Dark Gray | 84, 80, 69 | #545045 | 411C | Accent/text |
| KB Gold | - | - | 872 C | Special/metallic |
| KB Silver | - | - | 877 C | Special/metallic |
