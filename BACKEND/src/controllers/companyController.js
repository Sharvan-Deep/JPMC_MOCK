const companyService = require('../services/companyService');
const { parseCompanyListQuery } = require('../validators/companyQueryValidator');

async function listCompanies(req, res) {
  const options = parseCompanyListQuery(req.query);
  const result = await companyService.listCompanies(options);

  res.json({
    success: true,
    data: result,
  });
}

async function getCompanyById(req, res) {
  const company = await companyService.getCompanyById(req.params.companyId);

  res.json({
    success: true,
    data: { company },
  });
}

async function getCompanySummary(req, res) {
  const summary = await companyService.getCompanySummary(req.params.companyId);

  res.json({
    success: true,
    data: { summary },
  });
}

module.exports = {
  listCompanies,
  getCompanyById,
  getCompanySummary,
};
