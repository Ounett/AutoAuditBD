SET application_name='AutoAudit_Casos_Prueba';
DO $$
DECLARE v_id BIGINT; v_antes BIGINT; v_despues BIGINT; v_token TEXT := 'PRUEBA-'||txid_current()::text;
BEGIN
  SELECT count(*) INTO v_antes FROM auditoria.bitacora;
  INSERT INTO demo.productos(sku,nombre,precio,existencias) VALUES(v_token,'Hebilla de prueba',5,10)
    RETURNING producto_id INTO v_id;
  UPDATE demo.productos SET precio=7 WHERE producto_id=v_id;
  DELETE FROM demo.productos WHERE producto_id=v_id;
  SELECT count(*) INTO v_despues FROM auditoria.bitacora;
  IF v_despues-v_antes <> 5 THEN
    RAISE EXCEPTION 'Se esperaban 5 detalles auditados, hay %',v_despues-v_antes;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM auditoria.v_historial WHERE registro_pk->>'producto_id'=v_id::text AND operacion='UPDATE' AND columna='precio' AND valor_anterior='5.00' AND valor_nuevo='7.00') THEN
    IF NOT EXISTS(SELECT 1 FROM auditoria.v_historial WHERE registro_pk->>'producto_id'=v_id::text AND operacion='UPDATE' AND columna='precio' AND (valor_anterior)::numeric=5 AND (valor_nuevo)::numeric=7) THEN
      RAISE EXCEPTION 'No se encontraron valores anterior/nuevo del UPDATE';
    END IF;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM auditoria.v_historial WHERE registro_pk->>'producto_id'=v_id::text AND operacion='DELETE' AND fila_anterior IS NOT NULL AND fila_nueva IS NULL) THEN
    RAISE EXCEPTION 'DELETE no preservó la fila';
  END IF;
  RAISE NOTICE 'OK: INSERT + UPDATE + DELETE, 5 detalles, valores y borrado preservados (producto_id=%)',v_id;
END $$;
SELECT id_bitacora,fecha_hora,usuario,tabla,operacion,columna,valor_anterior,valor_nuevo,ip
FROM auditoria.v_historial ORDER BY id_bitacora DESC LIMIT 10;
