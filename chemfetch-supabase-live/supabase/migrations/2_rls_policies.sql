-- Enable RLS and define per-user access policies
ALTER TABLE user_chemical_watch_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_rows"
  ON user_chemical_watch_list
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "modify_own_rows"
  ON user_chemical_watch_list
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Optional: grant full access to service_role
CREATE POLICY "admin_access"
  ON user_chemical_watch_list
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
