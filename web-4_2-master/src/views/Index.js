import { useState, useEffect } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import Chart from "chart.js";
import { Bar } from "react-chartjs-2";
import { scaleLinear } from "d3-scale";
import koreaMapData from "../assets/skorea-submunicipalities-2018-topo-simple.json";
// [수정됨 1] Form 관련 컴포넌트 추가 Import
import {
    Button,
    Card,
    CardHeader,
    CardBody,
    Progress,
    Table,
    Container,
    Row,
    Col,
    Form,
    FormGroup,
    Input,
    Label
} from "reactstrap";

import {
    chartOptions,
    parseOptions,
    chartExample2,
} from "variables/charts.js";

import Header from "components/Headers/Header.js";

const Index = (props) => {
    const [mapData, setMapData] = useState([]);

    // 차트용 데이터
    const [chartData, setChartData] = useState({
        labels: [],
        datasets: []
    });

    // 테이블용 데이터
    const [tableData, setTableData] = useState([]);

    // [수정됨 2] 예측 모델 입력값 관리 State
    const [inputs, setInputs] = useState({
        region: 'Seoul', // 기본값
        age: '',
        visit_days: '',
        duration: ''
    });

    // [수정됨 3] 예측 결과값 저장 State
    const [predictionResult, setPredictionResult] = useState(null);

    const REGION_INFO = {
        'Seoul': { name: '서울', lat: 37.5665, lon: 126.9780, color: '#FF6384' },
        'Busan': { name: '부산', lat: 35.1795, lon: 129.0749, color: '#36A2EB' },
        'Daegu': { name: '대구', lat: 35.8714, lon: 128.6014, color: '#FFCE56' },
        'Incheon': { name: '인천', lat: 37.4563, lon: 126.7052, color: '#4BC0C0' },
        'Gwangju': { name: '광주', lat: 35.1595, lon: 126.8526, color: '#9966FF' },
        'Daejeon': { name: '대전', lat: 36.3504, lon: 127.3845, color: '#FF9F40' },
        'Ulsan': { name: '울산', lat: 35.5384, lon: 129.3114, color: '#FF6384' },
        'Sejong': { name: '세종', lat: 36.4800, lon: 127.2890, color: '#36A2EB' },
        'Gyeonggi-do': { name: '경기', lat: 37.4138, lon: 127.5183, color: '#FFCE56' },
        'Gangwon-do': { name: '강원', lat: 37.8228, lon: 128.1555, color: '#4BC0C0' },
        'Chungcheongbuk-do': { name: '충북', lat: 36.6350, lon: 127.4914, color: '#9966FF' },
        'Chungcheongnam-do': { name: '충남', lat: 36.6588, lon: 126.6728, color: '#FF9F40' },
        'Jeollabuk-do': { name: '전북', lat: 35.7175, lon: 127.1530, color: '#FF6384' },
        'Jeollanam-do': { name: '전남', lat: 34.8679, lon: 126.9910, color: '#36A2EB' },
        'Gyeongsangbuk-do': { name: '경북', lat: 36.4919, lon: 128.8889, color: '#FFCE56' },
        'Gyeongsangnam-do': { name: '경남', lat: 35.4606, lon: 128.2132, color: '#4BC0C0' },
        'Jeju': { name: '제주', lat: 33.4996, lon: 126.5312, color: '#FF9F40' },
    };

    const maxVal = Math.max(0, ...mapData.map(d => d.value));
    const popScale = scaleLinear().domain([0, maxVal || 100]).range([5, 20]);

    if (window.Chart) {
        parseOptions(Chart, chartOptions());
    }

    // [수정됨 4] 입력값이 바뀔 때 실행되는 함수
    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setInputs({
            ...inputs,
            [name]: value
        });
    };

    // [수정됨 5] '예측하기' 버튼 누르면 실행되는 함수
    const handlePredict = async () => {
        // 간단한 유효성 검사 (빈칸 방지)
        if(!inputs.age || !inputs.visit_days || !inputs.duration) {
            alert("나이, 방문일수, 이용시간을 모두 입력해주세요!");
            return;
        }

        try {
            // 백엔드(/predict)로 데이터 전송
            const response = await fetch('http://localhost:8000/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs),
            });

            const result = await response.json();

            if(response.ok) {
                // 성공 시 결과 State 업데이트
                setPredictionResult(result.prediction);
            } else {
                alert("예측 실패: " + result.detail);
            }
        } catch (error) {
            console.error("API 요청 실패:", error);
            alert("서버 연결에 실패했습니다.");
        }
    };

    useEffect(() => {
        const fetchAndAggregateData = async () => {
            try {
                const response = await fetch('http://localhost:8000/visualize');
                const rawData = await response.json();

                const regionSum = {};
                const ageSum = {};
                let grandTotal = 0;

                rawData.forEach(row => {
                    const value = row.total_payment_may || 0;
                    grandTotal += value;

                    const engName = row.region_city_group;
                    if (regionSum[engName]) regionSum[engName] += value;
                    else regionSum[engName] = value;

                    const ageName = row.age_group || "Unknown";
                    if (ageSum[ageName]) ageSum[ageName] += value;
                    else ageSum[ageName] = value;
                });

                const finalMapData = Object.keys(regionSum).map(engName => {
                    const info = REGION_INFO[engName];
                    if (!info) return null;
                    return {
                        name: info.name,
                        value: regionSum[engName],
                        lat: info.lat,
                        lon: info.lon,
                        color: info.color
                    };
                }).filter(item => item !== null);

                setMapData(finalMapData);

                const ORDERED_AGE_LABELS = ["10대 이하", "20대", "30대", "40대", "50대", "60대 이상"];
                const sortedValues = ORDERED_AGE_LABELS.map(label => ageSum[label] || 0);

                setChartData({
                    labels: ORDERED_AGE_LABELS,
                    datasets: [
                        {
                            label: '연령대별 매출',
                            data: sortedValues,
                            backgroundColor: '#fb6340',
                            barThickness: 20,
                            maxBarThickness: 30
                        },
                    ],
                });

                const finalTableData = ORDERED_AGE_LABELS.map(label => {
                    const val = ageSum[label] || 0;
                    const percent = grandTotal === 0 ? 0 : (val / grandTotal) * 100;

                    return {
                        age: label,
                        value: val,
                        percent: percent
                    };
                });

                setTableData(finalTableData);

            } catch (error) {
                console.error("데이터 로딩 실패:", error);
            }
        };

        fetchAndAggregateData();
    }, []);

    return (
        <>
            <Header />
            <Container className="mt--7" fluid>
                <Row>
                    <Col className="mb-5 mb-xl-0" xl="8">
                        <Card className="bg-gradient-default shadow">
                            <CardHeader className="bg-transparent">
                                <h2 className="text-white mb-0">지역별 매출 (지도)</h2>
                            </CardHeader>
                            <CardBody>
                                <div className="chart" style={{ height: '600px', width: '100%' }}>
                                    <ComposableMap
                                        projection="geoMercator"
                                        projectionConfig={{ scale: 4000, center: [127.5, 36] }}
                                        style={{ width: "100%", height: "100%" }}
                                    >
                                        <Geographies geography={koreaMapData}>
                                            {({ geographies }) =>
                                                geographies.map((geo) => (
                                                    <Geography
                                                        key={geo.rsmKey}
                                                        geography={geo}
                                                        fill="#EAEAEC"
                                                        stroke="#D6D6DA"
                                                        style={{
                                                            default: { outline: "none" },
                                                            hover: { fill: "#EAEAEC", outline: "none" },
                                                            pressed: { outline: "none" },
                                                        }}
                                                    />
                                                ))
                                            }
                                        </Geographies>
                                        {mapData.map((data, index) => (
                                            <Marker key={index} coordinates={[data.lon, data.lat]}>
                                                <circle
                                                    r={popScale(data.value)}
                                                    fill={data.color}
                                                    stroke="#fff"
                                                    strokeWidth={2}
                                                    style={{ opacity: 0.8, cursor: 'pointer' }}
                                                />
                                                <title>{data.name}: {data.value}</title>
                                            </Marker>
                                        ))}
                                    </ComposableMap>
                                </div>
                            </CardBody>
                        </Card>
                    </Col>
                    <Col xl="4">
                        <Card className="shadow">
                            <CardHeader className="bg-transparent">
                                <h2 className="mb-0">연령대별 매출</h2>
                            </CardHeader>
                            <CardBody>
                                <div className="chart">
                                    <Bar data={chartData} options={chartExample2.options} />
                                </div>
                            </CardBody>
                        </Card>
                    </Col>
                </Row>
                <Row className="mt-5">
                    {/* [수정됨 6] 매출 예측 입력 폼 및 결과 표시 영역 */}
                    <Col className="mb-5 mb-xl-0" xl="8">
                        <Card className="shadow">
                            <CardHeader className="border-0">
                                <Row className="align-items-center">
                                    <div className="col">
                                        <h3 className="mb-0">매출 예측 시뮬레이션</h3>
                                    </div>
                                </Row>
                            </CardHeader>
                            <CardBody>
                                <Form>
                                    <Row>
                                        <Col md="6">
                                            <FormGroup>
                                                <Label>지역 선택</Label>
                                                {/* Select 박스: REGION_INFO의 키들을 이용해 옵션 생성 */}
                                                <Input
                                                    type="select"
                                                    name="region"
                                                    value={inputs.region}
                                                    onChange={handleInputChange}
                                                >
                                                    {Object.keys(REGION_INFO).map(key => (
                                                        <option key={key} value={key}>
                                                            {REGION_INFO[key].name} ({key})
                                                        </option>
                                                    ))}
                                                </Input>
                                            </FormGroup>
                                        </Col>
                                        <Col md="6">
                                            <FormGroup>
                                                <Label>나이</Label>
                                                <Input
                                                    type="number"
                                                    name="age"
                                                    placeholder="예: 25"
                                                    value={inputs.age}
                                                    onChange={handleInputChange}
                                                />
                                            </FormGroup>
                                        </Col>
                                    </Row>
                                    <Row>
                                        <Col md="6">
                                            <FormGroup>
                                                <Label>월 방문 일수</Label>
                                                <Input
                                                    type="number"
                                                    name="visit_days"
                                                    placeholder="예: 5"
                                                    value={inputs.visit_days}
                                                    onChange={handleInputChange}
                                                />
                                            </FormGroup>
                                        </Col>
                                        <Col md="6">
                                            <FormGroup>
                                                <Label>총 이용 시간 (분)</Label>
                                                <Input
                                                    type="number"
                                                    name="duration"
                                                    placeholder="예: 120"
                                                    value={inputs.duration}
                                                    onChange={handleInputChange}
                                                />
                                            </FormGroup>
                                        </Col>
                                    </Row>
                                    <div className="text-center mt-3">
                                        <Button
                                            color="primary"
                                            type="button"
                                            onClick={handlePredict}
                                            size="lg"
                                        >
                                            예상 매출 확인하기
                                        </Button>
                                    </div>
                                </Form>

                                {/* 예측 결과가 있을 때만 보여주는 영역 */}
                                {predictionResult !== null && (
                                    <div className="mt-4 text-center bg-secondary p-4 rounded">
                                        <h3>예상 월 매출액</h3>
                                        <h1 className="text-success display-2 font-weight-bold">
                                            {predictionResult.toLocaleString()} 원
                                        </h1>
                                    </div>
                                )}
                            </CardBody>
                        </Card>
                    </Col>

                    {/* 하단 우측 테이블 */}
                    <Col xl="4">
                        <Card className="shadow">
                            <CardHeader className="border-0">
                                <h3 className="mb-0">연령대별 매출 비율</h3>
                            </CardHeader>
                            <Table className="align-items-center table-flush" responsive>
                                <thead className="thead-light">
                                <tr>
                                    <th scope="col">연령대</th>
                                    <th scope="col">총 매출 (원)</th>
                                    <th scope="col">비중 (%)</th>
                                </tr>
                                </thead>
                                <tbody>
                                {tableData.map((row, index) => (
                                    <tr key={index}>
                                        <th scope="row">{row.age}</th>
                                        <td>{row.value.toLocaleString()}</td>
                                        <td>
                                            <div className="d-flex align-items-center">
                                                <span className="mr-2">{row.percent.toFixed(1)}%</span>
                                                <div>
                                                    <Progress
                                                        max="100"
                                                        value={row.percent}
                                                        barClassName={
                                                            row.percent > 40 ? "bg-gradient-danger" :
                                                                row.percent > 20 ? "bg-gradient-success" :
                                                                    "bg-gradient-primary"
                                                        }
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </Table>
                        </Card>
                    </Col>
                </Row>
            </Container>
        </>
    );
};

export default Index;