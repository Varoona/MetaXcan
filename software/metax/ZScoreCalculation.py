__author__ = 'heroico'

import logging
import numpy
import math
import Exceptions


BETA_Z = "beta_z"
BETA_Z_SIGMA_REF = "beta_z_and_ref"
METAXCAN = "metaxcan"
METAXCAN_FROM_REFERENCE = "metaxcan_from_reference"

def ZScoreScheme(name):
    scheme = None
    if name == BETA_Z:
        scheme = _BetaZ()
    elif name == BETA_Z_SIGMA_REF:
        scheme = _BetaZAndRef()
    elif name == METAXCAN:
        scheme = _MetaXcan()
    elif name == METAXCAN_FROM_REFERENCE:
        scheme = _MetaXcanFromReference()
    else:
        raise Exception("Unknown zscore scheme %s", name if name else "None")
    return scheme

class ZScoreCalculation(object):
    def __call__(self, gene, weights, beta_sets, covariance_matrix, valid_rsids):
        raise Exception("Wrong!")
        return  None, None, None

    def getValue(self, set, rsid):
        if not rsid in set.values_by_key:
            logging.log(5, "rsid %s not in %s", rsid, "set" if set.name is None else set.name)
            return None
        value = set.values_by_key[rsid]
        if value == "NA":
            logging.log(5, "rsid %s doesnt have a value for %s", rsid, "set" if set.name is None else set.name)
            return None
        value = float(value)
        return value

    def get_beta_z(self, beta_sets, rsid):
        b_z = beta_sets["beta_z"]
        value = self.getValue(b_z, rsid)
        return value

    def get_beta(self, beta_sets, rsid):
        betas = beta_sets["beta"]
        value = self.getValue(betas, rsid)
        return value

    def get_sigma_l(self, beta_sets, rsid):
        sigma_l = beta_sets["sigma_l"]
        value = self.getValue(sigma_l, rsid)
        return value

    def get_reference_sigma_l(self, variances, rsid):
        if not rsid in variances:
            logging.log(5, "rsid %s not in variances", rsid)
            return None

        sigma_l = math.sqrt(variances[rsid])
        return sigma_l

class _BetaZ(ZScoreCalculation):
    def __call__(self, gene, weights, beta_sets, covariance_matrix, valid_rsids):
        weight_values, variances = preProcess(covariance_matrix, valid_rsids, weights, beta_sets)

        pre_zscore = "NA"
        n = 0
        #dot_product is Var(g)
        dot_product = numpy.dot(numpy.dot(numpy.transpose(weight_values), covariance_matrix), weight_values)
        if dot_product > 0:
            denominator = math.sqrt(float(dot_product))
            numerator_terms = []
            for rsid in valid_rsids:
                w = weights[rsid].weight

                b_z = self.beta_z(beta_sets, rsid)
                if b_z is None:
                    continue

                s_l = self.sigma_l(beta_sets, variances, rsid)
                if not s_l:
                    continue

                term = w * b_z * s_l
                numerator_terms.append(term)

            n = len(numerator_terms)
            if n > 0:
                numerator = sum(numerator_terms)
                pre_zscore = str(numerator/denominator)
            else:
                logging.log(7,"No terms for %s ", gene)

        return pre_zscore, str(n), str(dot_product)

    def beta_z(self, beta_sets, rsid):
        return self.get_beta_z(beta_sets, rsid)

    def sigma_l(self, beta_sets, variances, rsid):
        return self.get_sigma_l(beta_sets, rsid)

class _BetaZAndRef(_BetaZ):
    def sigma_l(self, beta_sets, variances, rsid):
        return self.get_reference_sigma_l(variances, rsid)

class _MetaXcan(ZScoreCalculation):
    def __call__(self, gene, weights, beta_sets, covariance_matrix, valid_rsids):
        weight_values, variances = preProcess(covariance_matrix, valid_rsids, weights, beta_sets)

        pre_zscore = "NA"
        n = 0
        #dot_product is Var(g)
        dot_product = numpy.dot(numpy.dot(numpy.transpose(weight_values), covariance_matrix), weight_values)
        if dot_product > 0:
            denominator = math.sqrt(float(dot_product))
            numerator_terms = []
            for rsid in valid_rsids:
                w = weights[rsid].weight

                b = self.get_beta(beta_sets, rsid)
                if b is None:
                    continue

                s_l = self.sigma_l(beta_sets, variances, rsid)
                if not s_l:
                    continue

                term = w * b * s_l**2
                numerator_terms.append(term)

            n = len(numerator_terms)
            if n > 0:
                numerator = sum(numerator_terms)
                pre_zscore = str(numerator/denominator)
            else:
                logging.log(7, "No terms for %s ", gene)

        return pre_zscore, str(n), str(dot_product)

    def sigma_l(self, beta_sets, variances, rsid):
        return self.get_sigma_l(beta_sets, rsid)

class _MetaXcanFromReference(_MetaXcan):
    def sigma_l(self, beta_sets, variances, rsid):
        return self.get_reference_sigma_l(variances, rsid)

def preProcess(covariance_matrix, valid_rsids, weights, beta_sets):
    b = None
    if "beta" in beta_sets:
        b = beta_sets["beta"]
    elif "beta_z" in beta_sets:
        b = beta_sets["beta_z"]

    weight_values = []
    variances = {}
    for i,rsid in enumerate(valid_rsids):
        if rsid not in weights:
            raise Exceptions.ReportableException("RSID %s can't be found in the weights database. Are you sure your covariance data matches the weights database you are using?" % (rsid))
        weight = weights[rsid].weight
        if b and (not rsid in b.values_by_key or b.values_by_key[rsid] == "NA"):
            logging.log(7, "snp %s not present in beta data, skipping weight")
            # this will effectively skip this rsid at (w * G * w)
            weight = 0
        weight_values.append(weight)
        if covariance_matrix.ndim == 0:
            variances[rsid] = float(covariance_matrix)
        else:
            variances[rsid] = covariance_matrix[i][i]
    return weight_values, variances
