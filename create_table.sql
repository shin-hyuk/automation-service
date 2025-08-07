-- SQL script to create data collection table in Supabase (first project: UTGL Gary wealth)
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS utgl_gary_wealth_records (
    date TIMESTAMPTZ DEFAULT NOW(),
    data JSONB NOT NULL
);

-- Create an index on date for time-based queries
CREATE INDEX IF NOT EXISTS idx_utgl_gary_wealth_records_date 
ON utgl_gary_wealth_records(date);

-- Add comments for documentation
COMMENT ON TABLE utgl_gary_wealth_records IS 'Data collection table for UTGL Gary wealth data (first project)';
COMMENT ON COLUMN utgl_gary_wealth_records.date IS 'Timestamp when the record was created';
COMMENT ON COLUMN utgl_gary_wealth_records.data IS 'Complete JSON payload received';

-- Note: More tables will be created as we add new data collection projects
