// src/components/SchoolSelector.js
import React from 'react';

const SCHOOLS = {
  'Academies': [
    'Orcutt Academy K-8',
    'Orcutt Academy High School'
  ],
  'Junior High Schools': [
    'Lakeview Junior High',
    'Orcutt Junior High'
  ],
  'Elementary Schools': [
    'Alice Shaw Elementary',
    'Joe Nightingale Elementary',
    'Olga Reed School K-8',
    'Patterson Road Elementary',
    'Pine Grove Elementary',
    'Ralph Dunlap Elementary'
  ],
  'Non-Traditional': [
    'Orcutt School for Independent Study'
  ]
};

const SchoolSelector = ({ selectedSchool, onSchoolChange }) => {
  return (
    <div className="school-selector">
      <h3>Select School</h3>
      <select 
        value={selectedSchool || ''} 
        onChange={(e) => onSchoolChange(e.target.value)}
        className="school-dropdown"
      >
        <option value="">All Schools</option>
        {Object.entries(SCHOOLS).map(([category, schools]) => (
          <optgroup key={category} label={category}>
            {schools.map(school => (
              <option key={school} value={school}>
                {school}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
};

export default SchoolSelector;