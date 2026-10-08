import React, { useState } from 'react';
import type { AnswerIn, QuestionnaireOut } from '../../types/risk_profile';

interface QuestionnaireFormProps {
  questionnaire: QuestionnaireOut;
  onSubmit: (answers: AnswerIn[]) => Promise<void>;
  onCancel?: () => void;
  isSubmitting?: boolean;
}

export const QuestionnaireForm: React.FC<QuestionnaireFormProps> = ({
  questionnaire,
  onSubmit,
  onCancel,
  isSubmitting = false,
}) => {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSelectOption = (questionCode: string, optionCode: string) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionCode]: optionCode,
    }));
    setValidationError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check all questions are answered
    const unanswered = questionnaire.questions.filter((q) => !selectedAnswers[q.code]);
    if (unanswered.length > 0) {
      setValidationError(`Please answer all questions (${unanswered.length} remaining).`);
      return;
    }

    const answers: AnswerIn[] = questionnaire.questions.map((q) => ({
      question_code: q.code,
      option_code: selectedAnswers[q.code] || '',
    }));

    await onSubmit(answers);
  };

  const answeredCount = Object.keys(selectedAnswers).length;
  const totalCount = questionnaire.questions.length;
  const progressPercent = totalCount > 0 ? (answeredCount / totalCount) * 100 : 0;

  return (
    <form className="questionnaire-form" onSubmit={handleSubmit}>
      <div className="questionnaire-header">
        <div>
          <h2 className="questionnaire-title">Risk Tolerance Questionnaire</h2>
          <p className="questionnaire-desc">
            Complete the 7-question assessment to determine your deterministic risk band.
          </p>
        </div>
        <div className="questionnaire-progress">
          <span className="progress-text">
            {answeredCount} of {totalCount} Answered
          </span>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </div>

      {validationError && (
        <div className="alert alert--warning" role="alert">
          {validationError}
        </div>
      )}

      <div className="questionnaire-list">
        {questionnaire.questions.map((q, idx) => (
          <div key={q.code} className="question-card" id={`question-${q.code}`}>
            <div className="question-card__header">
              <span className="question-number">Question {idx + 1}</span>
              <h3 className="question-prompt">{q.prompt}</h3>
            </div>
            <div className="options-grid" role="radiogroup" aria-labelledby={`question-${q.code}`}>
              {q.options.map((opt) => {
                const isSelected = selectedAnswers[q.code] === opt.code;
                return (
                  <label
                    key={opt.code}
                    className={`option-card ${isSelected ? 'option-card--selected' : ''}`}
                  >
                    <input
                      type="radio"
                      name={`question_${q.code}`}
                      value={opt.code}
                      checked={isSelected}
                      onChange={() => handleSelectOption(q.code, opt.code)}
                      disabled={isSubmitting}
                      className="option-radio"
                    />
                    <div className="option-indicator">
                      <div className="option-indicator__dot" />
                    </div>
                    <span className="option-label">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="questionnaire-actions">
        {onCancel && (
          <button
            type="button"
            className="btn btn--outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          className="btn btn--primary"
          disabled={isSubmitting || answeredCount < totalCount}
          id="submit-assessment-btn"
        >
          {isSubmitting ? 'Calculating Band...' : 'Submit Risk Assessment'}
        </button>
      </div>
    </form>
  );
};
