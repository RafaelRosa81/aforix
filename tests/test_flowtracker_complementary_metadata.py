from aforix.ingest.adapters.flowtracker_dis import FlowTrackerDISAdapter


def test_one_complementary_row_supplies_both_scale_fields():
    lines = [
        "Datos complementarios",
        " Registro        Fecha     Hora   Punto_de_aforo(m)   Lec_nivel_esc(m)  Caudal_estimado(m^3/s)  Comentarios",
        "     01  2023/06/06 11:34:52         0.000             0.020                 () A ABAJO PTE 30M ",
        "",
        "Control_Automatico_de_Calidad_(Beamcheck)",
    ]

    data = FlowTrackerDISAdapter()._extract_complementary_data(lines)

    assert data == {
        "scale_start_m": "0.020",
        "scale_end_m": "0.020",
        "complementary_end_datetime": "2023-06-06 11:34:52",
    }


def test_last_complementary_row_supplies_end_scale_and_datetime():
    lines = [
        "Datos_complementarios",
        "Registro Fecha Hora Punto_de_aforo(m) Lec_nivel_esc(m)",
        "01 2023/06/06 11:34:52 0.000 0.020",
        "02 2023/06/06 11:40:12 1.000 0.035",
        "",
    ]

    data = FlowTrackerDISAdapter()._extract_complementary_data(lines)

    assert data == {
        "scale_start_m": "0.020",
        "scale_end_m": "0.035",
        "complementary_end_datetime": "2023-06-06 11:40:12",
    }


def test_missing_complementary_table_sets_s_d_for_table_fields():
    data = FlowTrackerDISAdapter()._extract_complementary_data(
        ["File_Name 7013.TXT.WAD", "Operator(s) FMENDOZA", "St Clock Loc"]
    )

    assert data == {
        "scale_start_m": "S/D",
        "scale_end_m": "S/D",
        "complementary_end_datetime": "S/D",
    }


def test_spanish_operadores_key_normalizes_to_operators():
    adapter = FlowTrackerDISAdapter()

    assert adapter._summary_key("Operadores") == "operators"
