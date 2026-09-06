export interface MergeConflict {
    file: string;
    localContent: string;
    remoteContent: string;
    localEvalScore: number;
    remoteEvalScore: number;
}

export class SemanticMergeService {
    /**
     * Attempts to semantically merge two versions of a prompt based on their evaluation scores.
     * If the scores are vastly different, it will auto-resolve to the higher scoring prompt.
     * Otherwise, it will require manual resolution (returning a conflict).
     */
    public resolvePromptMerge(conflict: MergeConflict): { resolved: boolean, resolvedContent?: string, reason?: string } {
        // If the local version performs significantly better (e.g. >5% improvement)
        if (conflict.localEvalScore > conflict.remoteEvalScore + 5) {
            return {
                resolved: true,
                resolvedContent: conflict.localContent,
                reason: `Auto-resolved to local version (Score: ${conflict.localEvalScore}% vs ${conflict.remoteEvalScore}%)`
            };
        }
        
        // If the remote version performs significantly better
        if (conflict.remoteEvalScore > conflict.localEvalScore + 5) {
            return {
                resolved: true,
                resolvedContent: conflict.remoteContent,
                reason: `Auto-resolved to remote version (Score: ${conflict.remoteEvalScore}% vs ${conflict.localEvalScore}%)`
            };
        }

        // If scores are too close, flag as a manual conflict for human review
        return {
            resolved: false,
            reason: `Scores are too similar (${conflict.localEvalScore}% vs ${conflict.remoteEvalScore}%). Manual resolution required.`
        };
    }
}
