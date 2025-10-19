  Why Assertion Counts Vary By Table

  The number of assertions varies based on:

  1. Dataset Pattern Matching: Tests use dataset_pattern matching (e.g., *snowflake*covid19* vs *snowflake*demographics*)
  2. Column-Specific Tests: Many tests require specific columns to exist (e.g., column: "cases" only runs if that column exists)        
  3. Profile Data Availability: Some tests need specific profile metrics (min, max, mean, median, stddev, uniqueCount) which may not    
   be available for all column types
  4. Column Data Types: Numeric tests (min/max/mean) only work on numeric columns

  Complete Assertion Type Inventory

  Here's the full breakdown of all 20 assertion types:

  PROFILE-BASED TESTS (13 tests - Use cached DataHub profile data, no DB queries)

  Table-Level Profile Tests (4 tests)

  | Test Type                  | Status        | Description                     | Profile Data Needed |
  |----------------------------|---------------|---------------------------------|---------------------|
  | table_row_count            | ✅ IMPLEMENTED | Row count within min/max range  | profile.rowCount    |
  | table_row_count_equals     | ✅ IMPLEMENTED | Row count equals exact value    | profile.rowCount    |
  | table_column_count_equals  | ✅ IMPLEMENTED | Column count equals exact value | profile.columnCount |
  | table_column_count_between | ✅ IMPLEMENTED | Column count within range       | profile.columnCount |

  Column-Level Profile Tests (9 tests)

  | Test Type                        | Status        | Description                     | Profile Data Needed
        |
  |----------------------------------|---------------|---------------------------------|--------------------------------------------    
  ------|
  | column_values_not_null           | ✅ IMPLEMENTED | Column has no/few null values   | fieldProfile.nullCount
         |
  | column_values_unique             | ✅ IMPLEMENTED | All values are unique           | fieldProfile.uniqueCount,
  fieldProfile.nullCount |
  | column_min_between               | ✅ IMPLEMENTED | Minimum value within range      | fieldProfile.min
         |
  | column_max_between               | ✅ IMPLEMENTED | Maximum value within range      | fieldProfile.max
         |
  | column_mean_between              | ✅ IMPLEMENTED | Mean value within range         | fieldProfile.mean
         |
  | column_median_between            | ✅ IMPLEMENTED | Median value within range       | fieldProfile.median
         |
  | column_stddev_between            | ✅ IMPLEMENTED | Standard deviation within range | fieldProfile.stdev
         |
  | column_distinct_count_between    | ✅ IMPLEMENTED | Distinct count within range     | fieldProfile.uniqueCount
         |
  | column_unique_proportion_between | ✅ IMPLEMENTED | Proportion of unique values     | fieldProfile.uniqueCount, profile.rowCount    
         |
  | column_null_count_equals         | ✅ IMPLEMENTED | Null count equals exact value   | fieldProfile.nullCount
         |

  ---
  QUERY-BASED TESTS (7 tests - Execute SQL on source DB, requires connector)

  Column-Level Query Tests (6 tests)

  | Test Type                     | Status        | Description                             | Requires     |
  |-------------------------------|---------------|-----------------------------------------|--------------|
  | column_value_range            | ✅ IMPLEMENTED | All values within min/max (fresh check) | DB connector |
  | column_values_in_set          | ✅ IMPLEMENTED | All values in allowed set               | DB connector |
  | column_values_not_in_set      | ✅ IMPLEMENTED | No values in forbidden set              | DB connector |
  | column_values_match_regex     | ✅ IMPLEMENTED | All values match regex pattern          | DB connector |
  | column_values_not_match_regex | ✅ IMPLEMENTED | No values match forbidden regex         | DB connector |
  | column_length_between         | ✅ IMPLEMENTED | String length within range              | DB connector |

  Table-Level Query Tests (1 test)

  | Test Type        | Status        | Description                        | Requires     |
  |------------------|---------------|------------------------------------|--------------|
  | table_custom_sql | ✅ IMPLEMENTED | Custom SQL returns expected result | DB connector |

  ---
  Implementation Status Summary

  ✅ ALL 20 TEST TYPES ARE FULLY IMPLEMENTED!

  Current Configuration in Your Config File:
  - Uses 13 profile-based tests (table_has_data, reasonable_column_count, covid_cases_min_reasonable, etc.)
  - Does NOT use any query-based tests yet (no connector configured)

  ---
  Why Counts Vary - Detailed Breakdown

  Looking at data-quality-action-config.yaml:

  # Applies to ALL Snowflake tables (2 assertions per table)
  - table_has_data (pattern: *snowflake*)
  - reasonable_column_count (pattern: *snowflake*)

  # Applies ONLY to COVID19 tables (2 assertions per matching table)
  - covid_cases_min_reasonable (pattern: *snowflake*covid19*, column: "cases")
  - covid_deaths_min_reasonable (pattern: *snowflake*covid19*, column: "deaths")

  # Applies to ALL Snowflake tables BUT only if they have a "county" column (1 assertion)
  - reasonable_distinct_values (pattern: *snowflake*, column: "county")

  # And so on...

  Example Breakdown:

  | Table                                                        | Matching Tests                                         | Total       
  Assertions |
  |--------------------------------------------------------------|--------------------------------------------------------|---------    
  ---------|
  | covid19_data with columns: date, county, cases, deaths       | All 15 tests (2 table + 13 column matches)             | 15
           |
  | demographics with columns: fips, iso3166_2, total_population | 2 table + 9 column tests (no county/date/cases/deaths) | 11
           |
  | simple_table with columns: id, name                          | 2 table tests only (no matching columns)               | 2
           |

  ---
  Missing/Future Assertion Types

  Based on DataHub's assertion standards and common data quality patterns, here are additional assertion types that could be added:

  Profile-Based Additions (Could be added)

  1. ❌ column_null_proportion_between - Null percentage within range (currently only has equals)
  2. ❌ column_value_distribution - Check histogram/distribution shape
  3. ❌ column_quantile_between - Validate percentile values (p25, p75, p99)
  4. ❌ table_row_count_growth - Check row count change vs previous run
  5. ❌ column_cardinality_ratio - Distinct count / total count ratio

  Query-Based Additions (Could be added)

  6. ❌ column_freshness - Check timestamp columns for data recency
  7. ❌ table_row_count_comparison - Compare row counts between tables
  8. ❌ referential_integrity - FK values exist in parent table
  9. ❌ column_sum_equals - Sum of numeric column equals expected value
  10. ❌ column_values_sorted - Check if column is sorted (ASC/DESC)
  11. ❌ duplicate_row_count - Check for duplicate rows
  12. ❌ column_pattern_distribution - % of values matching pattern

  ---

● Summary

  Why assertion counts vary:
  - Your config has 15 total test definitions, but each applies to different dataset patterns and columns
  - A table gets only the tests whose dataset_pattern matches its URN AND whose column exists
  - Example: A COVID19 table with all matching columns could get all 15 assertions, while a simple 2-column table might only get 2      

  Current Implementation Status:

  ✅ 20/20 assertion types are FULLY IMPLEMENTED (100%)

  Breakdown:
  - ✅ 13 Profile-Based Tests - Work automatically from cached profile data
    - 4 table-level (row count, column count)
    - 9 column-level (nulls, uniqueness, min/max, mean, median, stddev, distinct count, proportions)
  - ✅ 7 Query-Based Tests - Require DB connector configuration
    - 6 column-level (value ranges, set membership, regex, string length)
    - 1 table-level (custom SQL)

  What you're currently using: Only the profile-based tests (13 of 20) because you haven't configured a Snowflake connector yet for     
  query-based tests.

  The 12 "missing" types I listed are potential future enhancements (freshness checks, referential integrity, row comparison, etc.)     
  that would require new code to be written.