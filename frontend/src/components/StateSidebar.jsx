import React from 'react';

const StateSidebar = ({ state }) => {
    // Helper to format values
    const formatValue = (val) => val === null || val === undefined ? "—" : val;
    const formatBool = (val) => val === true ? "Yes" : val === false ? "No" : "—";

    return (
        <div className="state-sidebar">
            <div className="sidebar-header">
                <h3>Medical Notes</h3>
                <div className="live-indicator">LIVE</div>
            </div>

            <div className="sidebar-content">
                {/* DEMOGRAPHICS */}
                <div className="section-card">
                    <h4>Patient Profile</h4>
                    <div className="stat-row">
                        <span>Female Age:</span>
                        <span className="stat-val">{formatValue(state?.demographics?.female_age)}</span>
                    </div>
                    <div className="stat-row">
                        <span>Male Age:</span>
                        <span className="stat-val">{formatValue(state?.demographics?.male_age)}</span>
                    </div>
                </div>

                {/* TIMELINE */}
                <div className="section-card">
                    <h4>Timeline</h4>
                    <div className="stat-row">
                        <span>Years Trying:</span>
                        <span className="stat-val">{formatValue(state?.fertility_timeline?.years_trying)}</span>
                    </div>
                </div>

                {/* HISTORY */}
                <div className="section-card">
                    <h4>Clinical History</h4>
                    <div className="stat-row">
                        <span>Prior Pregnancies:</span>
                        <span className={`stat-val ${state?.has_prior_pregnancies ? 'alert' : ''}`}>
                            {formatBool(state?.has_prior_pregnancies)}
                        </span>
                    </div>
                    <div className="stat-row">
                        <span>IVF Done:</span>
                        <span className="stat-val is-bool">
                            {formatBool(state?.treatments?.ivf?.done)}
                        </span>
                    </div>
                    <div className="stat-row">
                        <span>Tests Reviewed:</span>
                        <span className="stat-val">
                            {state?.reports_availability_checked ? "Checked" : "Pending"}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StateSidebar;
