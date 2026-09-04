/**
 * Central model registry — import models from here rather than individual files.
 */
const User = require('./User');
const EmailOTP = require('./EmailOTP');
const Invitation = require('./Invitation');
const RefreshToken = require('./RefreshToken');
const Company = require('./Company');
const Lead = require('./Lead');
const LeadNote = require('./LeadNote');
const LeadActivity = require('./LeadActivity');
const CSRPolicy = require('./CSRPolicy');
const Source = require('./Source');

module.exports = {
  User,
  EmailOTP,
  Invitation,
  RefreshToken,
  Company,
  Lead,
  LeadNote,
  LeadActivity,
  CSRPolicy,
  Source,
};
