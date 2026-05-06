#1 Inspect Data (Print all data)

SELECT *
FROM `inventory-forecasting-system.Online_retail_II.Inventry`
LIMIT 10;


#2 Clean Data and create new cleaned table

CREATE OR REPLACE TABLE `inventory-forecasting-system.Online_retail_II.retail_clean` AS
SELECT *
FROM `inventory-forecasting-system.Online_retail_II.Inventry`
WHERE Quantity > 0;

#print new cleaned table 

select * from `inventory-forecasting-system.Online_retail_II.retail_clean`;


#3 Daily SKU Aggregation

CREATE OR REPLACE TABLE `inventory-forecasting-system.Online_retail_II.retail_daily` AS
SELECT 
    CAST(StockCode AS STRING) AS StockCode,
    DATE(InvoiceDate) AS sale_date,
    SUM(Quantity) AS daily_units_sold,
    SUM(Quantity * Price) AS daily_revenue
FROM `inventory-forecasting-system.Online_retail_II.retail_clean`
GROUP BY StockCode, sale_date;


#print new retail_daily table

select * from `inventory-forecasting-system.Online_retail_II.retail_daily`;


#4 Sales Velocity (7-day Avg)

CREATE OR REPLACE TABLE `inventory-forecasting-system.Online_retail_II.retail_with_velocity` AS
SELECT 
    StockCode,
    sale_date,
    daily_units_sold,
    daily_revenue,

    AVG(daily_units_sold) OVER (
        PARTITION BY StockCode
        ORDER BY sale_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS avg_7day_sales

FROM `inventory-forecasting-system.Online_retail_II.retail_daily`;

#print new retail_with_velocity
select * from `inventory-forecasting-system.Online_retail_II.retail_with_velocity`;



#5 Demand Trend (Increasing or Decreasing)

CREATE OR REPLACE TABLE `inventory-forecasting-system.Online_retail_II.retail_with_trend` AS
SELECT 
    StockCode,
    sale_date,
    daily_units_sold,
    daily_revenue,
    avg_7day_sales,
    prev_avg_7day_sales,

    CASE 
        WHEN prev_avg_7day_sales IS NULL THEN 'Stable'
        WHEN avg_7day_sales > prev_avg_7day_sales THEN 'Increasing'
        WHEN avg_7day_sales < prev_avg_7day_sales THEN 'Decreasing'
        ELSE 'Stable'
    END AS demand_trend

FROM (
    SELECT 
        StockCode,
        sale_date,
        daily_units_sold,
        daily_revenue,
        avg_7day_sales,

        LAG(avg_7day_sales) OVER (
            PARTITION BY StockCode
            ORDER BY sale_date
        ) AS prev_avg_7day_sales

    FROM `inventory-forecasting-system.Online_retail_II.retail_with_velocity`
);

#Print retail with trend table
SELECT *
FROM `inventory-forecasting-system.Online_retail_II.retail_with_trend`
ORDER BY StockCode, sale_date;


#6 Risk Classification

CREATE OR REPLACE TABLE `inventory-forecasting-system.Online_retail_II.final_inventory_dataset` AS
SELECT *,
    
    CASE 
    -- 🔴 HIGH (strong + growing)
    WHEN avg_7day_sales > 26 AND demand_trend = 'Increasing' THEN 'High'

    -- 🟠 MEDIUM (strong OR moderate)
    WHEN avg_7day_sales > 26 THEN 'Medium'
    WHEN avg_7day_sales BETWEEN 12 AND 26 THEN 'Medium'

    -- 🟢 LOW
    ELSE 'Low'
    END AS risk_level

FROM `inventory-forecasting-system.Online_retail_II.retail_with_trend`;



#print final inventry dataset

select * from `inventory-forecasting-system.Online_retail_II.final_inventory_dataset`
order by StockCode,sale_date  asc;








