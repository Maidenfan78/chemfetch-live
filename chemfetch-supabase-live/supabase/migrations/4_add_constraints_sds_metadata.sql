-- Optional: Add helpful constraints
ALTER TABLE user_chemical_watch_list 
ADD CONSTRAINT check_risk_rating 
CHECK (risk_rating IN ('Extreme', 'High', 'Medium', 'Low') OR risk_rating IS NULL);

ALTER TABLE user_chemical_watch_list 
ADD CONSTRAINT check_consequence 
CHECK (consequence IN ('Catastrophic', 'Major', 'Moderate', 'Minor', 'Insignificant') OR consequence IS NULL);

ALTER TABLE user_chemical_watch_list 
ADD CONSTRAINT check_likelihood 
CHECK (likelihood IN ('Almost Certain', 'Likely', 'Possible', 'Unlikely', 'Rare') OR likelihood IS NULL);

ALTER TABLE user_chemical_watch_list 
ADD CONSTRAINT check_packing_group 
CHECK (packing_group IN ('I', 'II', 'III') OR packing_group IS NULL);