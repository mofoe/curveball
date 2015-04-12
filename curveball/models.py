#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of curveball.
# https://github.com/yoavram/curveball

# Licensed under the MIT license:
# http://www.opensource.org/licenses/MIT-license
# Copyright (c) 2015, Yoav Ram <yoavram+github@gmail.com>
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style("ticks")

from lmfit import Model


def logistic_function(t, y0, r, K):
    r"""The logistic growth model is the standard growth model in ecology.

    .. math::
        \frac{dy}{dt} = r y \Big(1 - \frac{y}{K}\Big) \Rightarrow
        y(t) = \frac{K}{1 - \Big(1 - \frac{K}{y_0} \Big)e^{-r t}}


    - :math:`y_0`: initial population size
    - K: maximum population size
    - r: initial growth rate per capita

    See also: `Wikipedia <http://en.wikipedia.org/wiki/Logistic_function>`_
    """
    return richards_function(t ,y0, r, K, 1.)


def richards_function(t, y0, r, K, nu):
    r"""Richards growth model (or the generalized logistic model) in a generalization of the logistic model that allows the inflection point to be anywhere along the curve.

    .. math::

        \frac{dy}{dt} = r y \Big( 1 - \Big(\frac{y}{K}\Big)^{\nu} \Big) \Rightarrow

        y(t) = \frac{K}{\Big[1 - \Big(1 - \Big(\frac{K}{y_0}\Big)^{\nu}\Big) e^{-r \nu t}\Big]^{1/\nu}}

    - :math:`y_0`: initial population size
    - K: maximum population size
    - r: initial growth rate per capita
    - :math:`\nu`: curvature of the logsitic term

    See also: `Wikipedia <http://en.wikipedia.org/wiki/Generalised_logistic_function>`_
    """
    return K / ((1 - (1 - (K/y0)**nu) * np.exp(-r * nu * t))**(1./nu))


def baranyi_roberts_function(t, y0, r, K, nu, q0, v):
    r"""The Baranyi-Roberts growth model is an extension of the Richards model that adds time lag.

    .. math::

        \frac{dy}{dt} = r \alpha(t) y \Big( 1 - \Big(\frac{y}{K}\Big)^{\nu} \Big) \Rightarrow

        y(t) = \frac{K}{\Big[1 - \Big(1 - \Big(\frac{K}{y_0}\Big)^{\nu}\Big) e^{-r \nu A(t)}\Big]^{1/\nu}}

        A(t) = \int_0^t{\alpha(s)ds} = \int_0^t{\frac{q_0}{q_0 + e^{-v t}} ds} = t + \frac{1}{v} \log{\Big( \frac{e^{-v t} + q0}{1 + q0} \Big)}


    - :math:`y_0`: initial population size
    - K: maximum population size
    - r: initial growth rate per capita
    - :math:`\nu`: curvature of the logsitic term
    - :math:`q_0`: initial adjustment to current environment
    - v: adjustment rate

    See also: `Baranyi, J., Roberts, T. a., 1994. A dynamic approach to predicting bacterial growth in food. Int. J. Food Microbiol. 23, 277–294. <www.ncbi.nlm.nih.gov/pubmed/7873331>`_
    """
    At = t + (1./v) * np.log((np.exp(-v * t) + q0)/(1 + q0))
    return K / ((1 - (1 - (K/y0)**nu) * np.exp( -r * nu * At ))**(1./nu))


def fit_model(df, well=None, ax=None, PLOT=True, PRINT=True):
    _df = df[df.Well == well].copy() if well != None else df.copy()
    models = []

    Kguess  = _df.OD.max()
    y0guess = _df.OD.min()
    nuguess = 1.0
    _df['dODdTime'] = np.gradient(_df.OD, _df.Time)
    rguess  = 4 * _df.dODdTime[~np.isinf(_df.dODdTime)].max() / Kguess
    params = baranyi_roberts_model.make_params(y0=y0guess, K=Kguess, r=rguess, nu=nuguess, q0=1.0, v=1.0)

    params['y0'].set(min=1-10)
    params['K'].set(min=1-10)
    params['r'].set(min=1-10)
    params['nu'].set(min=1-10)
    params['q0'].set(min=1e-10, max=1)
    params['v'].set(min=1e-10)

    # Baranyi - Roberts - full model (6 params)
    result = baranyi_roberts_model.fit(data=_df.OD, t=_df.Time, params=params)
    models.append(result)

    # Baranyi /w nu=1 = Logistic /w lag (5 params)
    params['q0'].set(vary=True)
    params['v'].set(vary=True)
    result = baranyi_roberts_model.fit(data=_df.OD, t=_df.Time, params=params)
    models.append(result)

    # Richards - no lag (4 params)
    params = richards_model.make_params(y0=y0guess, K=Kguess, r=rguess, nu=nuguess)
    params['y0'].set(min=1-10)
    params['K'].set(min=1-10)
    params['r'].set(min=1-10)
    params['nu'].set(min=1-10)
    result = richards_model.fit(data=_df.OD, t=_df.Time, params=params)
    models.append(result)

    # Logistic - nu=1 (3 params)
    params = logistic_model.make_params(y0=y0guess, K=Kguess, r=rguess)
    params['y0'].set(min=1-10)
    params['K'].set(min=1-10)
    params['r'].set(min=1-10)
    result = logistic_model.fit(data=_df.OD, t=_df.Time, params=params)
    models.append(result)

    # sort by increasing bic
    models.sort(key=lambda m: m.bic)

    # plot
    if PLOT:
        dy = _df.OD.max()/50
        dx = _df.Time.max()/25
        fig, ax = plt.subplots(1, len(models), sharex=True, sharey=True, figsize=(16,6))
        for i,fit in enumerate(models):
            vals = fit.best_values
            fit.plot_fit(ax=ax[i], datafmt='.', fit_kws={'lw':4})
            ax[i].axhline(y=vals['y0'], color='k', ls='--')
            ax[i].axhline(y=vals['K'], color='k', ls='--')
            if 'q0' in vals:
                lam = np.log(1. + 1./vals['q0']) / vals['v']
            else:
                lam = 0
            ax[i].axvline(x=lam, color='k', ls='--')
            ax[i].text(x=lam + dx, y=_df.OD.min() - 3*dy, s=r'$\lambda$')
            ax[i].set_title('Model: %s params, BIC: %d' % (fit.nvarys, fit.bic))
            ax[i].get_legend().set_visible(False)
            ax[i].set_xlim(0, 1.1 * _df.Time.max())
            ax[i].set_ylim(0, 1.1 * _df.OD.max())
            ax[i].set_xlabel('Time')
            ax[i].set_ylabel('')
        ax[0].set_ylabel('OD')
        sns.despine()
    if PRINT:
        print models[0].fit_report()
        vals = models[0].best_values
        lam = np.log(1. + 1./vals['q0']) / vals['v']
        print "lambda:", lam
    return models, ax


logistic_model = Model(logistic_function)
richards_model = Model(richards_function)
baranyi_roberts_model = Model(baranyi_roberts_function)
