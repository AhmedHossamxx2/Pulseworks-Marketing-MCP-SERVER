-- ===============================================================================
-- PULSEWORKS MARKETING - SEED DATA
-- Designed to test MCP protocol concerns: Elicitation, Notifications, and Safety
-- ===============================================================================

-- 1. Insert Employees
-- Mix of roles to test the 'Notifications' (tools/list_changed) requirement later.
INSERT INTO Employees (name, role) VALUES 
('Alice Manager', 'Account Executive'),
('Bob Writer', 'Copywriter'),
('Carol Director', 'Marketing Director'),
('David Analyst', 'Data Scientist');

-- 2. Insert Clients
-- Includes an inactive client to test defensive validation rules.
INSERT INTO Client (company_name, industry, status) VALUES 
('TechFlow Solutions', 'SaaS', 'active'),
('GreenEats Delivery', 'Food & Bev', 'active'),
('RetroKicks', 'Apparel', 'inactive');

-- 3. Insert Campaigns
-- Mix of platforms and statuses.
INSERT INTO Campaign (client_id, campaign_name, platform, status) VALUES 
(1, 'Q3 B2B Lead Gen', 'LinkedIn', 'live'),         -- campaign_id 1: Normal active campaign
(2, 'Summer Vegan Special', 'Meta', 'paused'),     -- campaign_id 2: Paused state testing
(2, 'TikTok Challenge 2026', 'TikTok', 'draft'),   -- campaign_id 3: Draft state testing
(3, 'Winter Blowout', 'Google', 'draft');          -- campaign_id 4: Tied to inactive client

-- 4. Insert Budgets
-- Tests defensive tool design: Campaign 2 is dangerously close to its limit.
INSERT INTO Budgets (campaign_id, daily_limit, total_spend, currency) VALUES 
(1, 500.00, 250.00, 'USD'),   -- Normal spend
(2, 100.00, 99.50, 'USD'),    -- Edge Case: 99.5% of daily limit spent (should trigger warnings)
(3, 1000.00, 0.00, 'USD');    -- Brand new budget

-- 5. Insert Advertisements
-- Tests 'Elicitation' (human-in-the-loop) and strict schema constraints (max 50 chars).
INSERT INTO Advertisements (campaign_id, approver_id, headline, body_text, approval_status) VALUES 
(1, 3, 'Boost Your Workflow Today!', 'Automate tasks with TechFlow.', 'live'), 
-- Ad 2: Edge Case -> NULL approver and 'pending_review' status. 
-- The LLM agent MUST trigger `elicitation/create` for Carol Director to approve this.
(1, NULL, 'Transform Your Business With TechFlow Automation', 'Sign up for a free trial.', 'pending_review'),
-- Ad 3: Edge Case -> Headline is exactly 50 characters (max length testing).
(2, 3, 'Fresh And Healthy Vegan Meals Delivered To You Now', 'Order today for 20% off.', 'live'),
(3, NULL, 'Dance To The Vegan Beat', 'Show us your best moves.', 'draft');

-- 6. Insert Working (Employee-to-Campaign Mappings)
-- Crucial for the 'tools/list_changed' requirement. Changing these roles at runtime 
-- should push a notification to the client granting/revoking tools.
INSERT INTO Working (employee_id, campaign_id, emp_role_in_campaign) VALUES 
(1, 1, 'Account Manager'),
(2, 1, 'Viewer'),      -- Bob can only use read-only tools here
(3, 1, 'Director'),    -- Carol has elicitation sign-off authority here
(4, 1, 'Analyst'),
(2, 3, 'Creator'),     -- Bob can draft ads here, but still needs Carol's approval
(3, 3, 'Director');