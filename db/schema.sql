-- 1. Create the Employees Table
-- This table must be created first as it is referenced by Working and Advertisements.
CREATE TABLE IF NOT EXISTS Employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL
);

-- 2. Create the Client Table
-- This table must be created early as it is referenced by the Campaign table.
CREATE TABLE IF NOT EXISTS Client (
    client_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    status ENUM('active', 'inactive') DEFAULT 'active'
);

-- 3. Create the Campaign Table
-- Links a campaign to a specific client.
CREATE TABLE IF NOT EXISTS Campaign (
    campaign_id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    platform ENUM('Google', 'Meta', 'TikTok', 'LinkedIn') NOT NULL,
    status ENUM('draft', 'live', 'paused') DEFAULT 'draft',
    FOREIGN KEY (client_id) REFERENCES Client(client_id) ON DELETE CASCADE
);

-- 4. Create the Budgets Table
-- Enforces a strict 1-to-1 relationship with the Campaign table using the UNIQUE constraint on campaign_id.
CREATE TABLE IF NOT EXISTS Budgets (
    budget_id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL UNIQUE,
    daily_limit DECIMAL(10, 2) NOT NULL,
    total_spend DECIMAL(10, 2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'USD',
    FOREIGN KEY (campaign_id) REFERENCES Campaign(campaign_id) ON DELETE CASCADE
);

-- 5. Create the Advertisements Table
-- Includes the added approver_id to support the mandatory 'Elicitation' (human-in-the-loop) requirement.
CREATE TABLE IF NOT EXISTS Advertisements (
    ad_id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL,
    approver_id INT,
    headline VARCHAR(50) NOT NULL,
    body_text TEXT,
    approval_status ENUM('draft', 'pending_review', 'live') DEFAULT 'draft',
    FOREIGN KEY (campaign_id) REFERENCES Campaign(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES Employees(employee_id) ON DELETE SET NULL
);

-- 6. Create the Working Table (Associative Entity)
-- Resolves the many-to-many relationship between Employees and Campaigns and tracks their specific role for notifications.
CREATE TABLE Working (
    employee_id INT NOT NULL,
    campaign_id INT NOT NULL,
    emp_role_in_campaign VARCHAR(100) NOT NULL,
    PRIMARY KEY (employee_id, campaign_id),
    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES Campaign(campaign_id) ON DELETE CASCADE
);

