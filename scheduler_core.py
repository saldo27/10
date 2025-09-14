"""
Scheduler Core Module

This module contains the main orchestration logic for the scheduler system,
extracted from the original Scheduler class to improve maintainability and separation of concerns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple, Any

from scheduler_config import SchedulerConfig
from exceptions import SchedulerError
from optimization_metrics import OptimizationMetrics
from operation_prioritizer import OperationPrioritizer
from progress_monitor import ProgressMonitor


class SchedulerCore:
    """
    Core orchestration class that manages the high-level scheduling workflow.
    This class focuses on coordination between components rather than implementation details.
    """
    
    def __init__(self, scheduler):
        """
        Initialize the scheduler core with enhanced optimization systems.
        
        Args:
            scheduler: Reference to the main Scheduler instance
        """
        self.scheduler = scheduler
        self.config = scheduler.config
        self.start_date = scheduler.start_date
        self.end_date = scheduler.end_date
        self.workers_data = scheduler.workers_data
        
        # Initialize enhancement systems
        self.metrics = OptimizationMetrics(scheduler)
        self.prioritizer = OperationPrioritizer(scheduler, self.metrics)
        self.progress_monitor = None  # Will be initialized in orchestrate_schedule_generation
        
        logging.info("SchedulerCore initialized with enhanced optimization systems")
    
    def orchestrate_schedule_generation(self, max_improvement_loops: int = 70) -> bool:
        """
        Main orchestration method for schedule generation workflow.
        
        Args:
            max_improvement_loops: Maximum number of improvement iterations
            
        Returns:
            bool: True if schedule generation was successful
        """
        logging.info("Starting schedule generation orchestration...")
        start_time = datetime.now()
        
        try:
            # Phase 1: Initialize schedule structure
            if not self._initialize_schedule_phase():
                raise SchedulerError("Failed to initialize schedule structure")
            
            # Phase 2: Assign mandatory shifts
            if not self._assign_mandatory_phase():
                raise SchedulerError("Failed to assign mandatory shifts")
            
            # Phase 3: Iterative improvement
            if not self._iterative_improvement_phase(max_improvement_loops):
                logging.warning("Iterative improvement phase completed with issues")
            
            # Phase 4: Finalization
            if not self._finalization_phase():
                raise SchedulerError("Failed to finalize schedule")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logging.info(f"Schedule generation orchestration completed successfully in {duration:.2f} seconds.")
            return True
            
        except Exception as e:
            logging.error(f"Schedule generation orchestration failed: {str(e)}", exc_info=True)
            if isinstance(e, SchedulerError):
                raise e
            else:
                raise SchedulerError(f"Orchestration failed: {str(e)}")
    
    def _initialize_schedule_phase(self) -> bool:
        """
        Phase 1: Initialize schedule structure and data.
        
        Returns:
            bool: True if initialization was successful
        """
        logging.info("Phase 1: Initializing schedule structure...")
        
        try:
            # Reset scheduler state
            self.scheduler.schedule = {}
            self.scheduler.worker_assignments = {w['id']: set() for w in self.workers_data}
            self.scheduler.worker_shift_counts = {w['id']: 0 for w in self.workers_data}
            self.scheduler.worker_weekend_counts = {w['id']: 0 for w in self.workers_data}
            self.scheduler.worker_posts = {w['id']: set() for w in self.workers_data}
            self.scheduler.last_assignment_date = {w['id']: None for w in self.workers_data}
            self.scheduler.consecutive_shifts = {w['id']: 0 for w in self.workers_data}
            
            # Initialize schedule with variable shifts
            self.scheduler._initialize_schedule_with_variable_shifts()
            
            # Create schedule builder
            from schedule_builder import ScheduleBuilder
            self.scheduler.schedule_builder = ScheduleBuilder(self.scheduler)
            
            logging.info(f"Schedule structure initialized with {len(self.scheduler.schedule)} dates")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize schedule phase: {str(e)}", exc_info=True)
            return False
    
    def _assign_mandatory_phase(self) -> bool:
        """
        Phase 2: Assign mandatory shifts and lock them in place.
        
        Returns:
            bool: True if mandatory assignment was successful
        """
        logging.info("Phase 2: Assigning mandatory shifts...")
        
        try:
            # Pre-assign mandatory shifts
            self.scheduler.schedule_builder._assign_mandatory_guards()
            
            # Synchronize tracking data
            self.scheduler.schedule_builder._synchronize_tracking_data()
            
            # Save initial state as best
            self.scheduler.schedule_builder._save_current_as_best(initial=True)
            
            # Log summary
            self.scheduler.log_schedule_summary("After Mandatory Assignment")
            
            logging.info("Mandatory assignment phase completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed in mandatory assignment phase: {str(e)}", exc_info=True)
            return False
    
    def _iterative_improvement_phase(self, max_improvement_loops: int) -> bool:
        """
        Phase 3: Enhanced iterative improvement with smart optimization.
        
        Args:
            max_improvement_loops: Maximum number of improvement iterations
            
        Returns:
            bool: True if improvement phase completed successfully
        """
        logging.info("Phase 3: Starting enhanced iterative improvement...")
        
        # Initialize progress monitor
        self.progress_monitor = ProgressMonitor(self.scheduler, max_improvement_loops)
        self.progress_monitor.start_monitoring()
        
        improvement_loop_count = 0
        overall_improvement_made = True
        
        try:
            # Aumentar el número de ciclos por defecto si no se especifica
            if max_improvement_loops < 120:
                max_improvement_loops = 120
                
            # Calculate initial score for comparison
            current_overall_score = self.metrics.calculate_overall_schedule_score()
            logging.info(f"Score inicial: {current_overall_score:.2f}")
            
            while overall_improvement_made and improvement_loop_count < max_improvement_loops:
                loop_start_time = datetime.now()
                improvement_loop_count += 1
                
                logging.info(f"--- Starting Enhanced Improvement Loop {improvement_loop_count} ---")
                
                # Get current state for decision making
                current_state = {
                    'empty_shifts_count': self.metrics.count_empty_shifts(),
                    'workload_imbalance': self.metrics.calculate_workload_imbalance(),
                    'weekend_imbalance': self.metrics.calculate_weekend_imbalance()
                }
                
                # Get dynamically prioritized operations
                prioritized_operations = self.prioritizer.prioritize_operations_dynamically()
                
                # Execute operations with enhanced tracking
                operation_results = {}
                cycle_improvement_made = False
                
                for operation_name, operation_func, priority in prioritized_operations:
                    try:
                        # Check if operation should be skipped
                        should_skip, skip_reason = self.prioritizer.should_skip_operation(
                            operation_name, current_state
                        )
                        
                        if should_skip:
                            logging.debug(f"Skipping {operation_name}: {skip_reason}")
                            operation_results[operation_name] = {
                                'improved': False,
                                'skipped': True,
                                'reason': skip_reason
                            }
                            continue
                        
                        # Measure performance of operation
                        before_score = self.metrics.calculate_overall_schedule_score()
                        operation_start_time = datetime.now()
                        
                        # Execute operation
                        if operation_name == "synchronize_tracking_data":
                            operation_func()
                            operation_made_change = True  # This operation always "succeeds"
                        else:
                            operation_made_change = operation_func()
                        
                        operation_end_time = datetime.now()
                        execution_time = (operation_end_time - operation_start_time).total_seconds()
                        
                        # Evaluate improvement quality
                        after_score = self.metrics.calculate_overall_schedule_score()
                        
                        if operation_made_change and operation_name != "synchronize_tracking_data":
                            is_significant, improvement_ratio = self.metrics.evaluate_improvement_quality(
                                before_score, after_score, operation_name
                            )
                            
                            if is_significant:
                                logging.info(f"✅ {operation_name}: mejora significativa "
                                           f"({improvement_ratio:.4f}, +{after_score-before_score:.2f})")
                                cycle_improvement_made = True
                            else:
                                logging.debug(f"⚠️  {operation_name}: mejora marginal "
                                            f"({improvement_ratio:.4f})")
                        
                        # Record operation results
                        operation_results[operation_name] = self.prioritizer.analyze_operation_effectiveness(
                            operation_name, before_score, after_score, execution_time
                        )
                        
                    except Exception as e:
                        logging.warning(f"Operation {operation_name} failed: {str(e)}")
                        operation_results[operation_name] = {
                            'improved': False,
                            'error': str(e)
                        }
                
                # Update current score after all operations
                current_overall_score = self.metrics.calculate_overall_schedule_score()
                
                # Track iteration progress with enhanced monitoring
                progress_data = self.progress_monitor.track_iteration_progress(
                    improvement_loop_count, operation_results, current_overall_score, current_state
                )
                
                # Record iteration for trend analysis
                self.metrics.record_iteration_result(
                    improvement_loop_count, operation_results, current_overall_score
                )
                
                # Check if should continue with smart early stopping
                should_continue, reason = self.metrics.should_continue_optimization(improvement_loop_count)
                if not should_continue:
                    logging.info(f"🛑 Parada temprana activada: {reason}")
                    break
                
                # Traditional improvement check as fallback
                overall_improvement_made = cycle_improvement_made
                
                # Log cycle summary
                loop_end_time = datetime.now()
                loop_duration = (loop_end_time - loop_start_time).total_seconds()
                successful_operations = sum(
                    1 for result in operation_results.values() 
                    if isinstance(result, dict) and result.get('improved', False)
                )
                
                logging.info(f"--- Loop {improvement_loop_count} completado en {loop_duration:.2f}s. "
                           f"Operaciones exitosas: {successful_operations}/{len(operation_results)} ---")
                
                if not overall_improvement_made:
                    logging.info("No se detectaron mejoras adicionales. Finalizando fase de mejora.")

            # Final summary
            if improvement_loop_count >= max_improvement_loops:
                termination_reason = f"Límite de iteraciones alcanzado ({max_improvement_loops})"
                logging.warning(termination_reason)
            else:
                termination_reason = "Convergencia alcanzada"
                
            # Display final optimization summary
            self.progress_monitor.display_optimization_summary(
                improvement_loop_count, current_overall_score, termination_reason
            )
            
            # Get performance insights for logging
            insights = self.progress_monitor.get_performance_insights()
            if not insights.get('error'):
                logging.info(f"📊 Insights finales: {insights['significant_improvements']} mejoras significativas, "
                           f"tasa de éxito: {insights['average_operations_success_rate']:.2f}")

            return True

        except Exception as e:
            logging.error(f"Error during enhanced iterative improvement phase: {str(e)}", exc_info=True)
            return False
    
    def _finalization_phase(self) -> bool:
        """
        Phase 4: Finalize the schedule and perform final optimizations.
        
        Returns:
            bool: True if finalization was successful
        """
        logging.info("Phase 4: Finalizing schedule...")
        
        try:
            # Final adjustment of last post distribution
            logging.info("Performing final last post distribution adjustment...")
            max_iterations = self.config.get('last_post_adjustment_max_iterations', 
                                           SchedulerConfig.DEFAULT_LAST_POST_ADJUSTMENT_ITERATIONS)

            if self.scheduler.schedule_builder._adjust_last_post_distribution(
                balance_tolerance=1.0,
                max_iterations=max_iterations
            ):
                logging.info("Final last post distribution adjustment completed.")


            # PASADA EXTRA: Llenar huecos y balancear tras el ajuste final
            logging.info("Extra pass: Filling empty shifts and balancing workloads after last post adjustment...")
            self.scheduler.schedule_builder._try_fill_empty_shifts()
            self.scheduler.schedule_builder._balance_workloads()
            self.scheduler.schedule_builder._balance_weekday_distribution()

            # Iterar hasta que todos los trabajadores estén dentro de la tolerancia ±1 en turnos y last posts
            max_final_balance_loops = 50
            for i in range(max_final_balance_loops):
                logging.info(f"Final strict balance loop {i+1}/{max_final_balance_loops}")
                changed1 = self.scheduler.schedule_builder._balance_workloads()
                changed2 = self.scheduler.schedule_builder._adjust_last_post_distribution(balance_tolerance=1.0, max_iterations=10)
                changed3 = self.scheduler.schedule_builder._balance_weekday_distribution()
                if not changed1 and not changed2 and not changed3:
                    logging.info(f"Balance achieved after {i+1} iterations")
                    break
            else:
                logging.warning(f"Max balance iterations ({max_final_balance_loops}) reached")

            # Get the best schedule
            final_schedule_data = self.scheduler.schedule_builder.get_best_schedule()

            if not final_schedule_data or not final_schedule_data.get('schedule'):
                logging.error("No best schedule data available for finalization.")
                return self._handle_fallback_finalization()

            # Update scheduler state with final schedule
            self._apply_final_schedule(final_schedule_data)

            # Final validation y logging
            self._perform_final_validation()

            logging.info("Schedule finalization phase completed successfully.")
            return True

        except Exception as e:
            logging.error(f"Error during finalization phase: {str(e)}", exc_info=True)
            return False
    
    def _handle_fallback_finalization(self) -> bool:
        """
        Handle fallback finalization when no best schedule is available.
        
        Returns:
            bool: True if fallback was successful
        """
        logging.warning("Using current schedule state as fallback for finalization.")
        
        if not self.scheduler.schedule or all(all(p is None for p in posts) for posts in self.scheduler.schedule.values()):
            logging.error("Current schedule state is also empty. Cannot finalize.")
            return False
        
        # Use current state as final schedule
        final_schedule_data = {
            'schedule': self.scheduler.schedule,
            'worker_assignments': self.scheduler.worker_assignments,
            'worker_shift_counts': self.scheduler.worker_shift_counts,
            'worker_weekend_counts': self.scheduler.worker_weekend_counts,
            'worker_posts': self.scheduler.worker_posts,
            'last_assignment_date': self.scheduler.last_assignment_date,
            'consecutive_shifts': self.scheduler.consecutive_shifts,
            'score': self.scheduler.calculate_score()
        }
        
        return self._apply_final_schedule(final_schedule_data)
    
    def _apply_final_schedule(self, final_schedule_data: Dict[str, Any]) -> bool:
        """
        Apply the final schedule data to the scheduler state.
        
        Args:
            final_schedule_data: Dictionary containing the final schedule data
            
        Returns:
            bool: True if application was successful
        """
        try:
            logging.info("Applying final schedule data to scheduler state...")
            
            self.scheduler.schedule = final_schedule_data['schedule']
            self.scheduler.worker_assignments = final_schedule_data['worker_assignments']
            self.scheduler.worker_shift_counts = final_schedule_data['worker_shift_counts']
            self.scheduler.worker_weekend_counts = final_schedule_data.get(
                'worker_weekend_shifts', 
                final_schedule_data.get('worker_weekend_counts', {})
            )
            self.scheduler.worker_posts = final_schedule_data['worker_posts']
            self.scheduler.last_assignment_date = final_schedule_data['last_assignment_date']
            self.scheduler.consecutive_shifts = final_schedule_data['consecutive_shifts']
            
            final_score = final_schedule_data.get('score', float('-inf'))
            logging.info(f"Final schedule applied with score: {final_score:.2f}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error applying final schedule data: {str(e)}", exc_info=True)
            return False
    
    def _perform_final_validation(self) -> bool:
        """
        Perform final validation and logging of the schedule.
        
        Returns:
            bool: True if validation passed
        """
        try:
            # Calculate final statistics
            total_slots_final = sum(len(slots) for slots in self.scheduler.schedule.values())
            total_assignments_final = sum(
                1 for slots in self.scheduler.schedule.values() 
                for worker_id in slots if worker_id is not None
            )
            
            empty_shifts_final = [
                (date, post_idx) 
                for date, posts in self.scheduler.schedule.items() 
                for post_idx, worker_id in enumerate(posts) 
                if worker_id is None
            ]
            
            # Validate schedule integrity
            if total_slots_final == 0:
                schedule_duration_days = (self.end_date - self.start_date).days + 1
                if schedule_duration_days > 0:
                    logging.error(f"Final schedule has 0 total slots despite valid date range ({schedule_duration_days} days).")
                    return False
            
            if total_assignments_final == 0 and total_slots_final > 0:
                logging.warning(f"Final schedule has {total_slots_final} slots but contains ZERO assignments.")
            
            if empty_shifts_final:
                empty_percentage = (len(empty_shifts_final) / total_slots_final) * 100
                logging.warning(f"Final schedule has {len(empty_shifts_final)} empty shifts ({empty_percentage:.1f}%) out of {total_slots_final} total slots.")
            
            # Log final summary
            self.scheduler.log_schedule_summary("Final Generated Schedule")
            
            return True
            
        except Exception as e:
            logging.error(f"Error during final validation: {str(e)}", exc_info=True)
            return False