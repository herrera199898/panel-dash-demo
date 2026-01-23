"""
Simulador de Producción en Tiempo Real
Ejecuta cambios automáticos en la base de datos para simular producción
"""
import time
import random
from datetime import datetime, timedelta
from demo_db_generator import DemoDatabaseGenerator

class ProductionSimulator:
    def __init__(self, db_path="demo_database.db", update_interval=30):
        """
        Args:
            db_path: Ruta a la base de datos SQLite
            update_interval: Segundos entre actualizaciones
        """
        self.db_path = db_path
        self.update_interval = update_interval
        self.generator = DemoDatabaseGenerator(db_path)
        self.is_running = False
        self.cambio_lote_timer = 0
        self.max_cambio_lote_interval = 300  # 5 minutos máximo para cambiar lote

    def start_simulation(self):
        """Iniciar simulación continua"""
        print("[START] Iniciando simulacion de produccion...")
        print(f"[INFO] Actualizacion cada {self.update_interval} segundos")
        print("[TARGET] Simulando cambios en tiempo real")

        self.is_running = True

        try:
            while self.is_running:
                self._update_cycle()
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            print("\n[STOP] Simulacion detenida por usuario")
        except Exception as e:
            print(f"\n❌ Error en simulación: {e}")
        finally:
            self.generator.close_connection()

    def stop_simulation(self):
        """Detener simulación"""
        self.is_running = False
        print("🛑 Deteniendo simulación...")

    def _update_cycle(self):
        """Ciclo de actualización de datos"""
        try:
            # Conectar a la base de datos
            self.generator.create_connection()

            # Actualizar datos de producción actual
            self.generator.update_production_data()

            # Actualizar datos del turno
            turno_actual = self._get_current_turn()
            self.generator.generate_turno_data(turno_actual)

            # Verificar si es momento de cambiar de lote
            self.cambio_lote_timer += self.update_interval
            if self.cambio_lote_timer >= self.max_cambio_lote_interval:
                # Probabilidad de cambiar lote (30%)
                if random.random() < 0.3:
                    self.generator.change_to_next_lote()
                    self.cambio_lote_timer = 0
                else:
                    # Reset timer con variación
                    self.cambio_lote_timer = random.randint(60, self.max_cambio_lote_interval)

            # Actualizar datos históricos (menos frecuente)
            if random.random() < 0.1:  # 10% de probabilidad
                self.generator.generate_historic_data(10)

            print(f"[OK] Datos actualizados - Turno {turno_actual} - {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            print(f"❌ Error en ciclo de actualización: {e}")
        finally:
            self.generator.close_connection()

    def _get_current_turn(self):
        """Determinar el turno actual basado en la hora"""
        now = datetime.now()
        current_time = now.time()

        # Turno 1: 08:00 - 20:00
        # Turno 2: 20:00 - 08:00
        turno1_start = datetime.strptime("08:00", "%H:%M").time()
        turno2_start = datetime.strptime("20:00", "%H:%M").time()

        if turno1_start <= current_time < turno2_start:
            return 1
        else:
            return 2

    def run_single_update(self):
        """Ejecutar una sola actualización para testing"""
        print("[UPDATE] Ejecutando actualizacion unica...")
        try:
            self.generator.create_connection()
            self.generator.update_production_data()
            turno = self._get_current_turn()
            self.generator.generate_turno_data(turno)
            print("[OK] Actualizacion completada")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.generator.close_connection()

    def simulate_production_burst(self, num_updates=10, interval=2):
        """Simular un burst de producción intensa"""
        print(f"[BURST] Simulando burst de produccion: {num_updates} actualizaciones cada {interval}s")

        for i in range(num_updates):
            try:
                self.generator.create_connection()
                # Actualización más agresiva para simular producción intensa
                self.generator.update_production_data(incrementar_progreso=True)

                # Aumentar datos del turno significativamente
                turno = self._get_current_turn()
                self.generator.generate_turno_data(turno)

                print(f"[BURST] Burst {i+1}/{num_updates} - {datetime.now().strftime('%H:%M:%S')}")

            except Exception as e:
                print(f"❌ Error en burst {i+1}: {e}")
            finally:
                self.generator.close_connection()

            if i < num_updates - 1:  # No esperar en la última iteración
                time.sleep(interval)

        print("[SUCCESS] Burst de produccion completado")

    def force_lote_change(self):
        """Forzar cambio inmediato de lote"""
        print("[CHANGE] Forzando cambio de lote...")
        try:
            self.generator.create_connection()
            lote_nuevo = self.generator.change_to_next_lote()
            if lote_nuevo:
                print(f"[OK] Lote cambiado a: {lote_nuevo['codigo_lote']}")
            else:
                print("[WARN] No se pudo cambiar lote (posiblemente no hay lotes disponibles)")
        except Exception as e:
            print(f"❌ Error cambiando lote: {e}")
        finally:
            self.generator.close_connection()

def main():
    """Función principal para ejecutar el simulador"""
    import argparse

    parser = argparse.ArgumentParser(description="Simulador de Producción Demo")
    parser.add_argument("--db", default="demo_database.db", help="Ruta a la base de datos")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo de actualización (segundos)")
    parser.add_argument("--mode", choices=["continuous", "single", "burst", "change"], default="continuous",
                       help="Modo de ejecución")

    args = parser.parse_args()

    simulator = ProductionSimulator(args.db, args.interval)

    if args.mode == "continuous":
        simulator.start_simulation()
    elif args.mode == "single":
        simulator.run_single_update()
    elif args.mode == "burst":
        simulator.simulate_production_burst()
    elif args.mode == "change":
        simulator.force_lote_change()

if __name__ == "__main__":
    main()