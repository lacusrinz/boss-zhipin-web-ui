# E2E Test Checklist: Monitoring Time Range Feature

**Test Date**: 2026-03-18
**Feature**: Enterprise Monitoring Time Range Configuration
**Test Type**: Manual End-to-End Verification

---

## Prerequisites

### Environment Setup
- [ ] Verify Python 3.8+ is installed
- [ ] Navigate to project root directory: `/Users/rinzlacus/Downloads/Coding/boss-zhipin-web-ui`
- [ ] Verify database file exists: `data/boss_jobs.db`
- [ ] Verify no other instances of the application are running

### Application Startup
- [ ] Start the web application:
  ```bash
  python code/web_app.py
  ```
- [ ] Verify application starts successfully (check console output for "Running on http://127.0.0.1:5000")
- [ ] Note the port number (default: 5000)

### Initial Access
- [ ] Open web browser and navigate to `http://127.0.0.1:5000`
- [ ] Verify the application homepage loads correctly
- [ ] Navigate to the "Enterprise Monitoring" page
  - [ ] Click on "Enterprise Monitoring" in the navigation menu
  - [ ] OR directly access `http://127.0.0.1:5000/monitoring`
- [ ] Verify the monitoring page loads with the configuration form and list

---

## Test Scenarios

### Scenario 1: Create Configuration with Time Range

**Test Case 1.1: Create Config with Valid Time Range (Same Day)**
- [ ] Fill in the "Enterprise Name" field (e.g., "测试企业A")
- [ ] Fill in the "Monitoring Keyword" field (e.g., "软件工程师")
- [ ] Select "Notification Frequency" (e.g., "实时推送")
- [ ] Fill in "Start Time" with a valid time in HH:MM format (e.g., "09:00")
- [ ] Fill in "End Time" with a valid time in HH:MM format (e.g., "18:00")
- [ ] Click the "Create Configuration" button
- [ ] **Expected Result**: Configuration created successfully
  - [ ] Success message displayed: "监控配置创建成功"
  - [ ] New configuration appears in the configuration list
  - [ ] Time range is displayed correctly in the list (e.g., "09:00-18:00")
  - [ ] Console log shows Beijing timezone handling (search for "东八区" or "UTC+8")

**Test Case 1.2: Create Config with Boundary Time Values**
- [ ] Fill in configuration details with start time "00:00"
- [ ] Fill in end time "23:59"
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Configuration created successfully
  - [ ] Success message displayed
  - [ ] Configuration appears in list with time range "00:00-23:59"

### Scenario 2: Verify Time Range Display

**Test Case 2.1: Check Time Range in Configuration List**
- [ ] Locate the newly created configuration in the list
- [ ] Verify the time range column displays the format "HH:MM-HH:MM"
- [ ] **Expected Result**: Time range is correctly displayed
  - [ ] Format is consistent (e.g., "09:00-18:00")
  - [ ] Start time and end time are separated by a hyphen
  - [ ] No timezone information is shown (user-facing is local time)

**Test Case 2.2: Verify Multiple Configurations Display**
- [ ] Create 2-3 additional configurations with different time ranges
- [ ] **Expected Result**: All configurations display correctly
  - [ ] Each configuration shows its respective time range
  - [ ] No overlap or confusion between configurations
  - [ ] List is scrollable if many configurations exist

### Scenario 3: Update Time Range

**Test Case 3.1: Modify Existing Time Range**
- [ ] Locate an existing configuration in the list
- [ ] Click the "Edit" button for that configuration
- [ ] Verify the form populates with existing values
- [ ] Modify the start time (e.g., change "09:00" to "08:30")
- [ ] Modify the end time (e.g., change "18:00" to "19:00")
- [ ] Click "Update Configuration"
- [ ] **Expected Result**: Configuration updated successfully
  - [ ] Success message displayed: "监控配置更新成功"
  - [ ] Configuration in list reflects new time range
  - [ ] Old time range is no longer displayed

**Test Case 3.2: Update Only Start Time**
- [ ] Edit a configuration
- [ ] Change only the start time, keep end time same
- [ ] Click "Update Configuration"
- [ ] **Expected Result**: Update successful
  - [ ] Only start time changed
  - [ ] End time remains unchanged

### Scenario 4: Invalid Time Format Handling

**Test Case 4.1: Invalid Format - Non-Numeric**
- [ ] Fill in configuration details
- [ ] Enter start time as "abc" (invalid format)
- [ ] Enter valid end time
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed: "时间格式无效，请使用 HH:MM 格式"
  - [ ] Configuration is NOT created
  - [ ] Form does not submit

**Test Case 4.2: Invalid Format - Missing Leading Zero**
- [ ] Enter start time as "9:00" (should be "09:00")
- [ ] Enter valid end time
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: May be accepted or rejected depending on validation
  - [ ] If accepted: verify it's normalized to "09:00"
  - [ ] If rejected: error message displayed

**Test Case 4.3: Invalid Format - Out of Range Hours**
- [ ] Enter start time as "25:00" (hours > 23)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed
  - [ ] Configuration is NOT created

**Test Case 4.4: Invalid Format - Out of Range Minutes**
- [ ] Enter start time as "09:60" (minutes > 59)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed
  - [ ] Configuration is NOT created

**Test Case 4.5: Invalid Format - Incorrect Separator**
- [ ] Enter start time as "09-00" (should use colon)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed
  - [ ] Configuration is NOT created

### Scenario 5: Cross-Day Time Range Validation

**Test Case 5.1: End Time Before Start Time (Cross-Day)**
- [ ] Fill in configuration details
- [ ] Enter start time as "18:00"
- [ ] Enter end time as "09:00" (earlier than start time)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed: "结束时间必须晚于开始时间"
  - [ ] Configuration is NOT created
  - [ ] User remains on form

**Test Case 5.2: Same Start and End Time**
- [ ] Enter start time as "12:00"
- [ ] Enter end time as "12:00" (same as start)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message displayed: "结束时间必须晚于开始时间"
  - [ ] Configuration is NOT created

### Scenario 6: Beijing Timezone Log Verification

**Test Case 6.1: Check Console Logs for Timezone**
- [ ] Perform any configuration creation or update
- [ ] Check the application console/logs
- [ ] Search for timezone-related messages
- [ ] **Expected Result**: Beijing timezone is logged
  - [ ] Log contains "东八区" or "UTC+8"
  - [ ] Log shows time conversion or timezone handling
  - [ ] Example log entry: "使用东八区时间处理监控时间范围"

**Test Case 6.2: Verify Time Storage**
- [ ] Create a configuration with specific time range
- [ ] Check the database (optional, for technical verification):
  ```bash
  sqlite3 data/boss_jobs.db "SELECT start_time, end_time FROM monitoring_configs WHERE enterprise_name='测试企业A';"
  ```
- [ ] **Expected Result**: Times are stored correctly in HH:MM format
  - [ ] No timezone offset stored (local time only)
  - [ ] Format matches input exactly

### Scenario 7: Edge Cases and Boundary Testing

**Test Case 7.1: Empty Time Fields**
- [ ] Leave start time empty
- [ ] Fill valid end time
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Form validation error
  - [ ] Error message about required fields
  - [ ] Configuration is NOT created

**Test Case 7.2: Midnight Time Range**
- [ ] Enter start time as "00:00"
- [ ] Enter end time as "00:01" (1 minute range)
- [ ] Click "Create Configuration"
- [ ] **Expected Result**: Configuration created successfully
  - [ ] Minimal valid time range accepted
  - [ ] Displayed as "00:00-00:01"

**Test Case 7.3: One Minute Before Midnight**
- [ ] Enter start time as "23:59"
- [ ] Enter end time as "23:59" (invalid - same time)
- [ ] **Expected Result**: Validation error (same as Test 5.2)

### Scenario 8: User Interface Validation

**Test Case 8.1: Time Input Field Type**
- [ ] Right-click on time input fields and select "Inspect Element"
- [ ] Verify the input type
- [ ] **Expected Result**: Input fields use appropriate type
  - [ ] `type="text"` with pattern validation OR
  - [ ] `type="time"` for browser-native time picker

**Test Case 8.2: Placeholder Text**
- [ ] Check time input fields before entering values
- [ ] **Expected Result**: Helpful placeholder text
  - [ ] Placeholder shows expected format (e.g., "HH:MM" or "09:00")
  - [ ] Placeholder is informative for users

**Test Case 8.3: Responsive Design**
- [ ] Resize browser window to mobile width (< 768px)
- [ ] Verify time range input and display
- [ ] **Expected Result**: Mobile-friendly layout
  - [ ] Time inputs remain accessible
  - [ ] Time range display doesn't overflow
  - [ ] Form remains usable on small screens

---

## Post-Test Verification

### Data Integrity Check
- [ ] Verify all test configurations are in database
- [ ] Check that no duplicate configurations were created
- [ ] Verify time ranges are stored in correct format

### Cleanup (Optional)
- [ ] Delete test configurations if needed
- [ ] Stop the web application (Ctrl+C in terminal)
- [ ] Verify application shut down cleanly

---

## Test Results Summary

**Date**: _______________
**Tester**: _______________

| Scenario | Status | Notes |
|----------|--------|-------|
| Prerequisites | [ ] Pass / [ ] Fail | |
| Scenario 1: Create Config | [ ] Pass / [ ] Fail | |
| Scenario 2: Display Time Range | [ ] Pass / [ ] Fail | |
| Scenario 3: Update Time Range | [ ] Pass / [ ] Fail | |
| Scenario 4: Invalid Format | [ ] Pass / [ ] Fail | |
| Scenario 5: Cross-Day Validation | [ ] Pass / [ ] Fail | |
| Scenario 6: Timezone Logs | [ ] Pass / [ ] Fail | |
| Scenario 7: Edge Cases | [ ] Pass / [ ] Fail | |
| Scenario 8: UI Validation | [ ] Pass / [ ] Fail | |

**Overall Result**: [ ] PASS / [ ] FAIL

**Issues Found**:
1. ________________________________________________
2. ________________________________________________
3. ________________________________________________

**Recommendations**:
1. ________________________________________________
2. ________________________________________________

---

## Additional Notes

- **Time Format**: All times should be in 24-hour HH:MM format
- **Timezone**: All times are interpreted as Beijing Time (UTC+8)
- **Validation**: Both frontend and backend validation should be tested
- **Logging**: Check application console for detailed logs during testing
- **Browser Compatibility**: Test in multiple browsers if possible (Chrome, Firefox, Safari)
