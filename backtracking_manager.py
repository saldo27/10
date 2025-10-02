"""
Backtracking Manager Module

This module provides intelligent backtracking capabilities for the scheduler,
allowing it to undo problematic assignments and recover from dead-end states.

Key Features:
- State checkpoint management
- Dead-end detection
- Intelligent rollback to optimal recovery points
- Assignment history tracking
- Automatic recovery mechanisms
"""

import logging
import copy
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ScheduleCheckpoint:
    """Represents a saved state of the schedule that can be restored."""
    
    # Identification
    checkpoint_id: str
    timestamp: datetime
    phase: str  # 'mandatory', 'improvement', 'finalization'
    iteration: int
    
    # Schedule state
    schedule: Dict[datetime, List[Optional[str]]]
    worker_assignments: Dict[str, Set[datetime]]
    worker_shift_counts: Dict[str, int]
    worker_weekend_counts: Dict[str, int]
    worker_posts: Dict[str, Set[int]]
    worker_post_counts: Dict[str, Dict[int, int]]
    
    # Tracking data
    last_assignment_date: Dict[str, Optional[datetime]]
    consecutive_shifts: Dict[str, int]
    worker_weekdays: Dict[str, Dict[int, int]]
    worker_weekends: Dict[str, List[datetime]]
    
    # Quality metrics
    score: float = 0.0
    empty_shifts: int = 0
    workload_imbalance: float = 0.0
    weekend_imbalance: float = 0.0
    constraint_violations: int = 0
    
    # Context
    description: str = ""
    reason: str = ""  # Why this checkpoint was created
    
    def __post_init__(self):
        """Ensure deep copies of mutable collections."""
        self.schedule = copy.deepcopy(self.schedule)
        self.worker_assignments = {k: v.copy() for k, v in self.worker_assignments.items()}
        self.worker_posts = {k: v.copy() for k, v in self.worker_posts.items()}
        self.worker_post_counts = copy.deepcopy(self.worker_post_counts)
        self.worker_weekdays = copy.deepcopy(self.worker_weekdays)
        self.worker_weekends = copy.deepcopy(self.worker_weekends)


@dataclass
class DeadEndIndicators:
    """Indicators that suggest the scheduler is in a dead-end state."""
    
    stagnation_iterations: int = 0
    no_improvement_cycles: int = 0
    constraint_violations: int = 0
    empty_shifts_stuck: int = 0
    severe_imbalance: bool = False
    impossible_assignments: int = 0
    
    def is_dead_end(self, thresholds: Dict[str, int]) -> bool:
        """Determine if current state is a dead-end."""
        return (
            self.stagnation_iterations >= thresholds.get('stagnation', 10) or
            self.no_improvement_cycles >= thresholds.get('no_improvement', 15) or
            self.constraint_violations >= thresholds.get('violations', 5) or
            (self.severe_imbalance and self.no_improvement_cycles >= 5) or
            self.impossible_assignments >= thresholds.get('impossible', 3)
        )


class BacktrackingManager:
    """
    Manages backtracking and recovery from problematic scheduling states.
    
    This system allows the scheduler to:
    1. Save checkpoints at strategic points
    2. Detect when it's stuck in a dead-end
    3. Rollback to a previous good state
    4. Try alternative paths
    """
    
    def __init__(self, scheduler, max_checkpoints: int = 20):
        """
        Initialize the backtracking manager.
        
        Args:
            scheduler: Reference to the main Scheduler instance
            max_checkpoints: Maximum number of checkpoints to keep in memory
        """
        self.scheduler = scheduler
        self.max_checkpoints = max_checkpoints
        
        # Checkpoint storage
        self.checkpoints: List[ScheduleCheckpoint] = []
        self.checkpoint_counter = 0
        
        # Dead-end detection
        self.dead_end_indicators = DeadEndIndicators()
        self.dead_end_thresholds = {
            'stagnation': 10,
            'no_improvement': 15,
            'violations': 5,
            'impossible': 3
        }
        
        # Recovery tracking
        self.rollback_history: List[Tuple[str, str, datetime]] = []  # (from_checkpoint, reason, timestamp)
        self.last_score = float('-inf')
        self.iterations_without_improvement = 0
        
        logging.info("BacktrackingManager initialized")
    
    def create_checkpoint(self, phase: str, iteration: int, 
                         description: str = "", reason: str = "manual") -> str:
        """
        Create a checkpoint of the current schedule state.
        
        Args:
            phase: Current phase of schedule generation
            iteration: Current iteration number
            description: Human-readable description
            reason: Why this checkpoint was created
            
        Returns:
            checkpoint_id: Unique identifier for this checkpoint
        """
        try:
            self.checkpoint_counter += 1
            checkpoint_id = f"cp_{phase}_{iteration}_{self.checkpoint_counter}"
            
            # Calculate quality metrics
            from optimization_metrics import OptimizationMetrics
            metrics = OptimizationMetrics(self.scheduler)
            
            score = metrics.calculate_overall_schedule_score()
            empty_shifts = metrics.count_empty_shifts()
            workload_imbalance = metrics.calculate_workload_imbalance()
            weekend_imbalance = metrics.calculate_weekend_imbalance()
            
            # Count constraint violations
            violations = len(self._count_violations())
            
            # Create checkpoint
            checkpoint = ScheduleCheckpoint(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                phase=phase,
                iteration=iteration,
                schedule=self.scheduler.schedule,
                worker_assignments=self.scheduler.worker_assignments,
                worker_shift_counts=self.scheduler.worker_shift_counts,
                worker_weekend_counts=self.scheduler.worker_weekend_counts,
                worker_posts=self.scheduler.worker_posts,
                worker_post_counts=self.scheduler.worker_post_counts,
                last_assignment_date=self.scheduler.last_assignment_date,
                consecutive_shifts=self.scheduler.consecutive_shifts,
                worker_weekdays=self.scheduler.worker_weekdays,
                worker_weekends=self.scheduler.worker_weekends,
                score=score,
                empty_shifts=empty_shifts,
                workload_imbalance=workload_imbalance,
                weekend_imbalance=weekend_imbalance,
                constraint_violations=violations,
                description=description,
                reason=reason
            )
            
            # Add to storage
            self.checkpoints.append(checkpoint)
            
            # Limit checkpoints in memory
            if len(self.checkpoints) > self.max_checkpoints:
                # Keep first and last, remove middle ones
                self.checkpoints = [self.checkpoints[0]] + self.checkpoints[-(self.max_checkpoints-1):]
            
            logging.info(f"✓ Checkpoint created: {checkpoint_id} (score: {score:.2f}, "
                        f"empty: {empty_shifts}, violations: {violations})")
            logging.debug(f"  Reason: {reason}, Description: {description}")
            
            return checkpoint_id
            
        except Exception as e:
            logging.error(f"Failed to create checkpoint: {e}", exc_info=True)
            return ""
    
    def detect_dead_end(self, current_score: float, empty_shifts: int, 
                       tolerance_violations: int = 0) -> bool:
        """
        Detect if the scheduler is in a dead-end state.
        
        Args:
            current_score: Current schedule quality score
            empty_shifts: Number of unfilled shifts
            tolerance_violations: Number of tolerance violations (optional)
            
        Returns:
            bool: True if dead-end detected
        """
        # Update indicators
        if current_score <= self.last_score:
            self.iterations_without_improvement += 1
            self.dead_end_indicators.no_improvement_cycles = self.iterations_without_improvement
        else:
            self.iterations_without_improvement = 0
            self.dead_end_indicators.no_improvement_cycles = 0
            self.last_score = current_score
        
        # Update other indicators
        self.dead_end_indicators.constraint_violations = len(self._count_violations())
        self.dead_end_indicators.empty_shifts_stuck = empty_shifts
        
        # Check for severe imbalance
        from optimization_metrics import OptimizationMetrics
        metrics = OptimizationMetrics(self.scheduler)
        workload_imbalance = metrics.calculate_workload_imbalance()
        weekend_imbalance = metrics.calculate_weekend_imbalance()
        self.dead_end_indicators.severe_imbalance = workload_imbalance > 4.0 or weekend_imbalance > 3.0
        
        # Check for persistent tolerance violations (NEW)
        if tolerance_violations > 0 and self.iterations_without_improvement >= 3:
            logging.warning(f"⚠️  Persistent tolerance violations detected: {tolerance_violations}")
            self.dead_end_indicators.severe_imbalance = True
        
        # Evaluate dead-end
        is_dead_end = self.dead_end_indicators.is_dead_end(self.dead_end_thresholds)
        
        if is_dead_end:
            logging.warning(f"⚠️  DEAD-END DETECTED:")
            logging.warning(f"   - No improvement: {self.dead_end_indicators.no_improvement_cycles} cycles")
            logging.warning(f"   - Violations: {self.dead_end_indicators.constraint_violations}")
            logging.warning(f"   - Empty shifts: {self.dead_end_indicators.empty_shifts_stuck}")
            logging.warning(f"   - Severe imbalance: {self.dead_end_indicators.severe_imbalance}")
            logging.warning(f"   - Weekend imbalance: {weekend_imbalance:.2f}")
            if tolerance_violations > 0:
                logging.warning(f"   - Tolerance violations: {tolerance_violations}")
        
        return is_dead_end
    
    def find_best_rollback_point(self) -> Optional[ScheduleCheckpoint]:
        """
        Find the best checkpoint to rollback to.
        
        Strategy:
        1. Prefer recent checkpoints (less work lost)
        2. Prefer higher quality scores
        3. Avoid checkpoints with similar problems
        
        Returns:
            ScheduleCheckpoint or None if no suitable checkpoint found
        """
        if not self.checkpoints:
            logging.warning("No checkpoints available for rollback")
            return None
        
        # Score each checkpoint for rollback suitability
        scored_checkpoints = []
        
        for cp in self.checkpoints:
            # Base score from quality
            rollback_score = cp.score
            
            # Penalize old checkpoints (prefer recent)
            age_penalty = (len(self.checkpoints) - self.checkpoints.index(cp)) * 0.1
            rollback_score -= age_penalty
            
            # Penalize checkpoints with violations
            rollback_score -= cp.constraint_violations * 100
            
            # Penalize checkpoints with many empty shifts
            rollback_score -= cp.empty_shifts * 10
            
            # Penalize checkpoints with imbalance
            rollback_score -= cp.workload_imbalance * 50
            
            scored_checkpoints.append((rollback_score, cp))
        
        # Sort by rollback score
        scored_checkpoints.sort(key=lambda x: x[0], reverse=True)
        
        best_checkpoint = scored_checkpoints[0][1]
        
        logging.info(f"🔄 Best rollback point: {best_checkpoint.checkpoint_id}")
        logging.info(f"   Score: {best_checkpoint.score:.2f}, "
                    f"Empty: {best_checkpoint.empty_shifts}, "
                    f"Violations: {best_checkpoint.constraint_violations}")
        
        return best_checkpoint
    
    def rollback_to_checkpoint(self, checkpoint: ScheduleCheckpoint) -> bool:
        """
        Restore scheduler state from a checkpoint.
        
        Args:
            checkpoint: The checkpoint to restore
            
        Returns:
            bool: True if rollback successful
        """
        try:
            logging.info(f"⏮️  Rolling back to checkpoint: {checkpoint.checkpoint_id}")
            
            # Restore schedule state
            self.scheduler.schedule = copy.deepcopy(checkpoint.schedule)
            self.scheduler.worker_assignments = {k: v.copy() for k, v in checkpoint.worker_assignments.items()}
            self.scheduler.worker_shift_counts = checkpoint.worker_shift_counts.copy()
            self.scheduler.worker_weekend_counts = checkpoint.worker_weekend_counts.copy()
            self.scheduler.worker_posts = {k: v.copy() for k, v in checkpoint.worker_posts.items()}
            self.scheduler.worker_post_counts = copy.deepcopy(checkpoint.worker_post_counts)
            
            # Restore tracking data
            self.scheduler.last_assignment_date = checkpoint.last_assignment_date.copy()
            self.scheduler.consecutive_shifts = checkpoint.consecutive_shifts.copy()
            self.scheduler.worker_weekdays = copy.deepcopy(checkpoint.worker_weekdays)
            self.scheduler.worker_weekends = copy.deepcopy(checkpoint.worker_weekends)
            
            # Reset dead-end indicators
            self.dead_end_indicators = DeadEndIndicators()
            self.iterations_without_improvement = 0
            self.last_score = checkpoint.score
            
            # Record rollback
            self.rollback_history.append((
                checkpoint.checkpoint_id,
                f"Dead-end recovery",
                datetime.now()
            ))
            
            logging.info(f"✓ Rollback successful - restored to score: {checkpoint.score:.2f}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to rollback to checkpoint: {e}", exc_info=True)
            return False
    
    def auto_recovery(self, metrics=None, tolerance_violations: int = 0) -> bool:
        """
        Automatically detect dead-end and attempt recovery.
        
        Args:
            metrics: Optional OptimizationMetrics instance (reuses if provided)
            tolerance_violations: Number of tolerance violations (optional)
        
        Returns:
            bool: True if recovery was performed
        """
        if metrics is None:
            from optimization_metrics import OptimizationMetrics
            metrics = OptimizationMetrics(self.scheduler)
        
        current_score = metrics.calculate_overall_schedule_score()
        empty_shifts = metrics.count_empty_shifts()
        
        if self.detect_dead_end(current_score, empty_shifts, tolerance_violations):
            logging.warning("🚨 Dead-end detected - initiating auto-recovery...")
            
            best_checkpoint = self.find_best_rollback_point()
            if best_checkpoint:
                if self.rollback_to_checkpoint(best_checkpoint):
                    logging.info("✓ Auto-recovery successful")
                    
                    # Notify optimization metrics about the rollback
                    if hasattr(metrics, 'record_rollback'):
                        metrics.record_rollback(best_checkpoint.checkpoint_id, best_checkpoint.score)
                    
                    return True
                else:
                    logging.error("✗ Auto-recovery failed during rollback")
            else:
                logging.error("✗ Auto-recovery failed - no suitable checkpoint")
        
        return False
    
    def should_create_checkpoint(self, iteration: int, phase: str) -> bool:
        """
        Determine if a checkpoint should be created based on iteration and phase.
        
        Integrates with adaptive iteration management.
        
        Args:
            iteration: Current iteration number
            phase: Current phase ('mandatory', 'improvement', 'finalization')
            
        Returns:
            bool: True if checkpoint should be created
        """
        # Always checkpoint at phase boundaries
        if phase in ['mandatory', 'finalization']:
            return True
        
        # During improvement phase
        if phase == 'improvement':
            # Every 10 iterations
            if iteration % 10 == 0:
                return True
            
            # If we have significant improvement (check last score)
            if len(self.checkpoints) > 0:
                last_checkpoint = self.checkpoints[-1]
                from optimization_metrics import OptimizationMetrics
                metrics = OptimizationMetrics(self.scheduler)
                current_score = metrics.calculate_overall_schedule_score()
                
                # Create checkpoint if improvement > 5%
                if current_score > last_checkpoint.score * 1.05:
                    return True
        
        return False
    
    def _count_violations(self) -> List[str]:
        """Count current constraint violations."""
        violations = []
        
        try:
            for worker_id, assignments in self.scheduler.worker_assignments.items():
                if not assignments:
                    continue
                
                sorted_dates = sorted(assignments)
                
                # Check gap between shifts
                for i in range(len(sorted_dates) - 1):
                    days_diff = (sorted_dates[i + 1] - sorted_dates[i]).days
                    if days_diff < self.scheduler.gap_between_shifts:
                        violations.append(f"Worker {worker_id}: gap violation")
        except Exception as e:
            logging.debug(f"Error counting violations: {e}")
        
        return violations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about backtracking system."""
        return {
            'total_checkpoints': len(self.checkpoints),
            'total_rollbacks': len(self.rollback_history),
            'current_checkpoint_count': len(self.checkpoints),
            'iterations_without_improvement': self.iterations_without_improvement,
            'last_score': self.last_score,
            'dead_end_indicators': {
                'stagnation': self.dead_end_indicators.stagnation_iterations,
                'no_improvement': self.dead_end_indicators.no_improvement_cycles,
                'violations': self.dead_end_indicators.constraint_violations,
                'severe_imbalance': self.dead_end_indicators.severe_imbalance
            }
        }
