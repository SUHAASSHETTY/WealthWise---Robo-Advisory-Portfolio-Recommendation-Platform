import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  getQuestionnaire,
  getRiskProfile,
  getRiskProfileHistory,
  submitAssessment,
} from '../../api/riskProfileApi';
import type {
  AnswerIn,
  HistoryEntryOut,
  QuestionnaireOut,
  RiskProfileOut,
} from '../../types/risk_profile';
import { RiskBandCard } from './RiskBandCard';
import { QuestionnaireForm } from './QuestionnaireForm';
import { AssessmentHistoryTable } from './AssessmentHistoryTable';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';

export const RiskProfilePage: React.FC = () => {
  const { token, persona } = useAuth();
  const [profile, setProfile] = useState<RiskProfileOut | null>(null);
  const [history, setHistory] = useState<HistoryEntryOut[]>([]);
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireOut | null>(null);
  const [isQuestionnaireOpen, setIsQuestionnaireOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadProfileData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [profileRes, historyRes] = await Promise.all([
        getRiskProfile(token),
        getRiskProfileHistory(token),
      ]);
      setProfile(profileRes);
      setHistory(historyRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load risk profile.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProfileData();
    setIsQuestionnaireOpen(false);
  }, [token, persona]);

  const handleStartQuestionnaire = async () => {
    setError(null);
    try {
      const q = await getQuestionnaire(token);
      setQuestionnaire(q);
      setIsQuestionnaireOpen(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load questionnaire.';
      setError(msg);
    }
  };

  const handleSubmitAnswers = async (answers: AnswerIn[]) => {
    if (!questionnaire) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await submitAssessment(token, {
        policy_version_id: questionnaire.policy_version_id,
        answers,
      });
      setSuccessMessage(
        `Assessment completed! Assigned band: ${result.assigned_band} (Score: ${result.total_score})`,
      );
      setIsQuestionnaireOpen(false);
      await loadProfileData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit assessment.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading risk profile data..." />;
  }

  return (
    <div className="feature-page risk-profile-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Risk Profile & Assessment</h2>
          <p className="page-subtitle">
            Deterministic risk profiling based on your investment horizon, goals, and risk capacity.
          </p>
        </div>
      </div>

      {error && <Alert type="error" title="Action Failed" message={error} onClose={() => setError(null)} />}
      {successMessage && (
        <Alert
          type="success"
          title="Success"
          message={successMessage}
          onClose={() => setSuccessMessage(null)}
        />
      )}

      {isQuestionnaireOpen && questionnaire ? (
        <div className="card questionnaire-container">
          <QuestionnaireForm
            questionnaire={questionnaire}
            onSubmit={handleSubmitAnswers}
            onCancel={() => setIsQuestionnaireOpen(false)}
            isSubmitting={isSubmitting}
          />
        </div>
      ) : (
        <div className="risk-profile-content">
          {profile && (
            <RiskBandCard
              profile={profile}
              onRetakeQuestionnaire={handleStartQuestionnaire}
            />
          )}
          <AssessmentHistoryTable history={history} />
        </div>
      )}
    </div>
  );
};
