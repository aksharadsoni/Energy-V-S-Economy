#
# ⚡ Energy–Economy Disconnect

## Overview

Energy–Economy Disconnect is an interactive Snowflake dashboard that explores the relationship between energy consumption and economic growth, with a primary focus on India, China, and the United States.

Instead of simply displaying historical statistics, the dashboard identifies periods where energy use and economic performance move differently — revealing patterns, disparities, and potential areas for further investigation.

## 🎯 The Problem

Economic growth and energy consumption are often analyzed separately.

Our project asks a different question:

> Where do energy consumption and economic growth stop telling the same story?

A country may experience strong economic growth without an equivalent increase in energy consumption, while another may experience rapidly increasing energy demand without proportional economic growth.

These disconnects can reveal important underlying patterns that traditional dashboards may overlook.

## 🌍 Countries Analyzed

The dashboard primarily focuses on:

- 🇮🇳 India
- 🇨🇳 China
- 🇺🇸 United States

Additional countries are also available for exploration and comparison.

India is additionally benchmarked against the G7 economies to provide broader international context.

## 🔍 Key Features

### 1. Energy Comparison

Compares absolute energy indicators for India, China, and the United States over time, preserving the real differences between countries rather than normalizing their starting values.

### 2. Economic Comparison

Tracks economic indicators across the three countries and highlights differences in their economic trajectories.

### 3. Energy–Economy Disconnect Engine

Identifies periods where changes in economic performance and energy consumption significantly diverge.

The dashboard uses these differences as signals for further investigation, rather than assuming causation.

### 4. "What Doesn't Add Up?"

Surfaces the most significant country-year disconnects in a concise table, allowing users to quickly identify unusual periods without manually examining decades of data.

### 5. Country Snapshots

Provides quick summaries of India, China, and the United States using comparable energy and economic indicators.

### 6. Current Pressures & Possible Responses

Connects the analysis to current energy and economic challenges and highlights potential areas that governments, businesses, and infrastructure planners could investigate.

### 7. India vs G7

Compares India's energy and economic trajectory with:

- Canada
- France
- Germany
- Italy
- Japan
- United Kingdom
- United States

This helps place India's development and energy requirements within the context of major developed economies.

### 8. Explore Other Countries

Users can select additional countries and compare their energy–economy relationship against the three primary economies.

## 💡 What Makes It Different?

Traditional dashboards answer:

> "What happened?"

Energy–Economy Disconnect goes one step further:

> "What doesn't add up?"

Rather than overwhelming users with graphs and tables, the dashboard attempts to automatically surface unusual relationships between energy consumption and economic performance.

## 🗄️ Data

The project uses public datasets available through Snowflake, including energy and economic time-series data.

The dashboard preserves absolute values for major country comparisons while using percentage changes where appropriate to detect energy–economy disconnects.

Missing data is not treated as zero, and observed relationships are presented as associations rather than causal claims.

## 🛠️ Built With

- Snowflake
- Snowflake Cortex / Cortex Code
- Streamlit
- SQL
- Public energy and economic datasets available through Snowflake

## 🚀 Goal

Our goal is to transform complex energy and economic data into an intuitive decision-support tool that helps users quickly identify:

Disparities → Disconnects → Hidden Patterns → Current Challenges → Areas to Investigate

## 👥 Team

Built during a HackDays Ahmedabad by Team Energy

Team Members:
- Akshara Soni
- Megh Shah
- Vaibhav Thakkar
```
