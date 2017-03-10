import 'babel-polyfill';
import React from 'react';
import ReactDOM from 'react-dom';
import PlayerWidget from './PlayerWidget';
import Card from './Card';

class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = { players: [], openCards: [] };
    }

    componentDidMount() {
        this.fetchData();
        setInterval(this.fetchData.bind(this), 1000);
    }

    fetchData() {
        fetch(window.DATA_URL, { credentials: 'same-origin' })
            .then(response => response.json())
            .then(json => this.setState(json));
    }

    findPlayer(position) {
        for (let i = 0; i < this.state.players.length; i++) {
            const player = this.state.players[i];
            if (player.position === position) {
                return player;
            }
        }
        return null;
    }

    renderPlayer(position) {
        const player = this.findPlayer(position);
        if (player) {
            return <PlayerWidget key={position} {...player} />;
        }

        return <div key={position} className="player-widget"/>;
    }

    renderPlayerList(positions) {
        if (!positions) {
            return null;
        }

        return (
            <div className="player-list">
                {positions.map(position => this.renderPlayer(position))}
            </div>
        );
    }

    renderOpenCard(card) {
        return <Card key={card} name={card} size="large"/>;
    }

    renderOpenCards() {
        return (
            <div className="open-cards">
                {this.state.openCards.map(this.renderOpenCard)}
            </div>
        );
    }

    render() {
        return (
            <div>
                {this.renderPlayerList([1, 2, 3, 4])}
                {this.renderOpenCards()}
                {this.renderPlayerList([8, 7, 6, 5])}
            </div>
        );
    }
}

ReactDOM.render(<App />, document.querySelector('.app'));
